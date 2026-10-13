import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["WEBHOOK_SECRET"] = "test-secret"
os.environ["DEMO_MODE"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "store_url", "https://shop.example.com")
    monkeypatch.setattr(settings, "consumer_key", "ck_test")
    monkeypatch.setattr(settings, "consumer_secret", "cs_test")
    monkeypatch.setattr(settings, "followup_statuses", ["completed"])
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    s = SessionLocal()
    yield s
    s.close()


def woo_order(oid=101, status="processing", customer_id=7, email="ana@example.com",
              first="Ana", last="Lopez", total="59.00"):
    return {"id": oid, "number": str(oid), "status": status, "currency": "USD", "total": total,
            "date_created_gmt": "2026-10-01T10:00:00", "customer_id": customer_id,
            "billing": {"first_name": first, "last_name": last, "email": email, "phone": "555-1"},
            "line_items": [{"product_id": 1, "name": "Coffee", "quantity": 2, "price": "29.50"}]}


def woo_customer(cid=7, email="ana@example.com", first="Ana", last="Lopez"):
    return {"id": cid, "email": email, "first_name": first, "last_name": last,
            "billing": {"phone": "555-1", "city": "Lisbon", "country": "PT"}}
