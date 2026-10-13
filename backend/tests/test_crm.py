import json

import httpx
from sqlalchemy import func, select

from app.models import Customer, FollowUpTask, Order, SyncLog
from app.services import sync
from app.services.webhook import compute_signature
from app.services.woo_client import WooClient
from tests.conftest import woo_customer, woo_order


def seed(db):
    for c in (woo_customer(7), woo_customer(8, "ben@example.com", "Ben", "Carter")):
        sync.upsert_customer(db, "woocommerce", sync.normalize_customer(c))
    for o in (woo_order(101, "processing"), woo_order(102, "completed", 8, "ben@example.com", "Ben", "Carter"),
              woo_order(103, "completed", 0, "guest@example.com", "Gus", "Guest")):
        sync.upsert_order(db, "woocommerce", sync.normalize_order(o))
    db.commit()


def signed_post(client, payload, secret="test-secret", topic="order.updated"):
    body = json.dumps(payload).encode()
    return client.post("/api/webhooks/woocommerce", content=body, headers={
        "X-WC-Webhook-Signature": compute_signature(secret, body), "X-WC-Webhook-Topic": topic})


def mock_client(handler):
    return WooClient("https://shop.example.com", "ck", "cs", transport=httpx.MockTransport(handler))


# 1-2
def test_health_and_db_init(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["database"] == "ok"


# 3
def test_customers_list_and_search(client, db):
    seed(db)
    assert client.get("/api/customers").json()["total"] == 3  # 2 registered + 1 guest profile
    r = client.get("/api/customers", params={"q": "carter"}).json()
    assert r["total"] == 1 and r["items"][0]["name"] == "Ben Carter"
    assert r["items"][0]["total_orders"] == 1
    assert client.get("/api/customers", params={"q": "%"}).json()["total"] == 0  # wildcard escaped
    guest = [c for c in client.get("/api/customers").json()["items"] if c["is_guest"]]
    assert guest and guest[0]["email"] == "guest@example.com"


# 4
def test_orders_list_and_filter(client, db):
    seed(db)
    assert client.get("/api/orders").json()["total"] == 3
    done = client.get("/api/orders", params={"status": "completed"}).json()
    assert done["total"] == 2 and all(o["status"] == "completed" for o in done["items"])
    assert client.get("/api/orders", params={"q": "101"}).json()["total"] == 1
    detail = client.get(f"/api/orders/{done['items'][0]['id']}").json()
    assert detail["items"][0]["name"] == "Coffee"


# 5
def test_interaction_create_and_read(client, db):
    seed(db)
    cid = db.scalar(select(Customer.id).where(Customer.email == "ana@example.com"))
    r = client.post(f"/api/customers/{cid}/interactions", json={"type": "call", "summary": "Called about shipping"})
    assert r.status_code == 201
    got = client.get(f"/api/customers/{cid}/interactions").json()
    assert got[0]["summary"] == "Called about shipping"
    assert client.post(f"/api/customers/{cid}/interactions", json={"summary": "   "}).status_code == 422


# 6
def test_followup_create_and_complete(client, db):
    seed(db)
    cid = db.scalar(select(Customer.id).where(Customer.email == "ana@example.com"))
    r = client.post("/api/follow-ups", json={"customer_id": cid, "title": "Check delivery", "due_date": "2026-11-01"})
    assert r.status_code == 201 and r.json()["status"] == "pending"
    tid = r.json()["id"]
    done = client.patch(f"/api/follow-ups/{tid}", json={"status": "completed"}).json()
    assert done["status"] == "completed" and done["completed_at"]
    assert client.get("/api/follow-ups", params={"status": "pending"}).json() == []
    assert client.post("/api/follow-ups", json={"customer_id": 9999, "title": "x", "due_date": "2026-11-01"}).status_code == 404


# 7
def test_resync_does_not_duplicate(client, db):
    def handler(request):
        page = int(request.url.params.get("page", 1))
        res = request.url.path.rsplit("/", 1)[-1]
        if res == "customers":
            data = [woo_customer(7), woo_customer(8, "ben@example.com", "Ben", "Carter")]
        else:
            data = [woo_order(101), woo_order(102, "completed", 8, "ben@example.com", "Ben", "Carter"),
                    woo_order(103, "completed", 0, "guest@example.com", "Gus", "Guest")]
        return httpx.Response(200, json=data, headers={"X-WP-TotalPages": "1", "X-WP-Total": str(len(data))})

    for _ in range(2):
        out = sync.sync_woocommerce(db, mock_client(handler))
    assert out["stats"]["orders"]["updated"] == 3 and out["stats"]["orders"]["created"] == 0
    assert db.scalar(select(func.count(Order.id))) == 3
    assert db.scalar(select(func.count(Customer.id))) == 3
    r = client.get("/api/integrations/woocommerce/status").json()
    assert r["state"] == "connected" and r["last_sync_at"]


def test_sync_pagination(db):
    calls = []

    def handler(request):
        page = int(request.url.params["page"])
        res = request.url.path.rsplit("/", 1)[-1]
        calls.append((res, page))
        data = [woo_order(200 + page)] if res == "orders" else [woo_customer(30 + page, f"c{page}@example.com")]
        return httpx.Response(200, json=data, headers={"X-WP-TotalPages": "3", "X-WP-Total": "3"})

    sync.sync_woocommerce(db, mock_client(handler))
    assert ("orders", 3) in calls and db.scalar(select(func.count(Order.id))) == 3


# 8
def test_invalid_webhook_signature_rejected(client, db):
    body = json.dumps(woo_order(500, "completed")).encode()
    r = client.post("/api/webhooks/woocommerce", content=body,
                    headers={"X-WC-Webhook-Signature": "bogus", "X-WC-Webhook-Topic": "order.created"})
    assert r.status_code == 401
    assert client.post("/api/webhooks/woocommerce", content=body).status_code == 401
    wrong = signed_post(client, woo_order(500, "completed"), secret="other-secret")
    assert wrong.status_code == 401
    assert db.scalar(select(func.count(Order.id))) == 0


def test_malformed_payload_after_valid_signature(client):
    body = b"{not json"
    r = client.post("/api/webhooks/woocommerce", content=body,
                    headers={"X-WC-Webhook-Signature": compute_signature("test-secret", body),
                             "X-WC-Webhook-Topic": "order.created"})
    assert r.status_code == 400


# 9
def test_repeated_webhook_is_idempotent(client, db):
    payload = woo_order(300, "completed")
    first = signed_post(client, payload, topic="order.created")
    assert first.status_code == 200 and first.json()["follow_up_created"] is True
    second = signed_post(client, payload, topic="order.created")
    assert second.json()["status"] == "duplicate"
    # A re-sent event with different bytes but the same order+status must not add another task.
    third = signed_post(client, {**payload, "note": "retry"}, topic="order.updated")
    assert third.status_code == 200 and third.json()["follow_up_created"] is False
    assert db.scalar(select(func.count(Order.id))) == 1
    assert db.scalar(select(func.count(FollowUpTask.id))) == 1


def test_webhook_updates_existing_order_status(client, db):
    seed(db)
    r = signed_post(client, woo_order(101, "completed"))
    assert r.json()["previous_status"] == "processing"
    assert db.scalar(select(Order.status).where(Order.woo_order_id == 101)) == "completed"
    assert db.scalar(select(func.count(Order.id))) == 3


# 10
def test_failed_connection_reports_error(client, db):
    def handler(request):
        raise httpx.ConnectError("boom")

    try:
        sync.sync_woocommerce(db, mock_client(handler))
        assert False, "expected WooError"
    except Exception as exc:
        assert "Could not connect" in str(exc)
    assert db.scalar(select(func.count(Order.id))) == 0
    st = client.get("/api/integrations/woocommerce/status").json()
    assert st["state"] == "error" and st["failure_count"] == 1 and st["last_sync_at"] is None


def test_sync_endpoint_errors(client, monkeypatch):
    monkeypatch.setattr(sync, "build_client", lambda: mock_client(lambda r: httpx.Response(401, json={})))
    r = client.post("/api/integrations/woocommerce/sync")
    assert r.status_code == 502 and "rejected" in r.json()["detail"]
    from app.config import settings
    monkeypatch.setattr(settings, "consumer_key", "")
    assert client.post("/api/integrations/woocommerce/sync").status_code == 400


def test_demo_mode_is_separate(client, db):
    seed(db)
    assert client.post("/api/integrations/woocommerce/sync").status_code != 409
    client.post("/api/integrations/mode", json={"mode": "demo"})
    assert client.get("/api/customers").json()["total"] == 0  # real data hidden in demo mode
    assert client.post("/api/integrations/demo/seed").status_code == 200
    assert client.get("/api/customers").json()["total"] > 5
    assert client.post("/api/integrations/woocommerce/sync").status_code == 409
    sim = client.post("/api/integrations/demo/simulate-order").json()
    assert sim["status"] == "processed" and sim["follow_up_created"] is True
    assert client.post("/api/integrations/demo/simulate-order", params={"replay": True}).json()["status"] == "duplicate"
    client.post("/api/integrations/mode", json={"mode": "real"})
    assert client.get("/api/customers").json()["total"] == 3
