"""Clearly labelled demo data. Stored with source='demo' so it never mixes with real records."""
import json
import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import SOURCE_DEMO, Customer, FollowUpTask, Interaction, Order, utcnow
from . import sync, webhook
from .app_settings import get_value, set_value

NAMES = [("Amara", "Okafor"), ("Liam", "Chen"), ("Sofia", "Marques"), ("Noah", "Williams"),
         ("Priya", "Nair"), ("Elena", "Petrova"), ("Marcus", "Johnson"), ("Yuki", "Tanaka"),
         ("Fatima", "Al-Sayed"), ("Oliver", "Schmidt"), ("Chloe", "Dubois"), ("Daniel", "Kowalski")]
PRODUCTS = [(11, "Organic Coffee Beans 1kg", "24.50"), (12, "Ceramic Pour-Over Set", "42.00"),
            (13, "Insulated Travel Mug", "18.99"), (14, "Cold Brew Starter Kit", "35.00"),
            (15, "Reusable Filter Pack", "9.50"), (16, "Espresso Tamper", "29.00")]
STATUSES = ["completed"] * 8 + ["processing"] * 4 + ["pending", "on-hold", "cancelled", "refunded", "failed"]
GUESTS = [("Hannah", "Reed", "hannah.reed"), ("Tom", "Baker", "tom.baker")]


def _raw_order(oid, woo_cid, first, last, email, status, when, rng):
    items = []
    for pid, name, price in rng.sample(PRODUCTS, rng.randint(1, 3)):
        items.append({"product_id": pid, "name": name, "quantity": rng.randint(1, 2), "price": price})
    total = sum(float(i["price"]) * i["quantity"] for i in items)
    return {"id": oid, "number": str(oid), "status": status, "currency": "USD",
            "total": f"{total:.2f}", "date_created_gmt": when.strftime("%Y-%m-%dT%H:%M:%S"),
            "customer_id": woo_cid,
            "billing": {"first_name": first, "last_name": last, "email": email,
                        "phone": f"+1 555 01{oid % 100:02d}"},
            "line_items": items}


def seed_demo(db: Session) -> dict:
    rng = random.Random(42)
    now = utcnow()
    created_c = created_o = 0
    for i, (first, last) in enumerate(NAMES, start=1):
        raw = {"id": 500 + i, "first_name": first, "last_name": last,
               "email": f"{first}.{last}@example.com".lower().replace(" ", ""),
               "billing": {"phone": f"+1 555 02{i:02d}", "city": "Springfield", "country": "US"}}
        _, created = sync.upsert_customer(db, SOURCE_DEMO, sync.normalize_customer(raw))
        created_c += created
    oid = 1000
    for _ in range(26):
        oid += 1
        idx = rng.randrange(len(NAMES))
        first, last = NAMES[idx]
        email = f"{first}.{last}@example.com".lower()
        when = now - timedelta(days=rng.randint(0, 90), hours=rng.randint(0, 20))
        raw = _raw_order(oid, 501 + idx, first, last, email, rng.choice(STATUSES), when, rng)
        _, created, _ = sync.upsert_order(db, SOURCE_DEMO, sync.normalize_order(raw))
        created_o += created
    for first, last, local in GUESTS:  # guest checkouts (customer_id = 0)
        oid += 1
        raw = _raw_order(oid, 0, first, last, f"{local}@example.com", "processing",
                         now - timedelta(days=rng.randint(0, 10)), rng)
        _, created, _ = sync.upsert_order(db, SOURCE_DEMO, sync.normalize_order(raw))
        created_o += created
    # A few starter notes/tasks so the communication screens are not empty.
    first_cust = db.scalar(select(Customer).where(Customer.source == SOURCE_DEMO)
                           .order_by(Customer.woo_customer_id))
    if first_cust and not db.scalar(select(func.count(Interaction.id)).where(
            Interaction.customer_id == first_cust.id)):
        db.add(Interaction(customer_id=first_cust.id, type="call",
                           summary="Demo note: asked about bulk pricing for office coffee."))
        db.add(FollowUpTask(customer_id=first_cust.id, title="Demo task: send bulk pricing sheet",
                            due_date=(now + timedelta(days=2)).date(),
                            external_event_id="demo:seed:bulk-pricing"))
    db.commit()
    return {"customers_created": created_c, "orders_created": created_o}


def simulate_order_event(db: Session, replay: bool = False) -> dict:
    """Demo-only: build a signed 'order completed' webhook and run it through the REAL handler
    (signature check, idempotency, upsert, follow-up rule). Not a delivery from WooCommerce."""
    from ..config import settings
    if replay:
        stored = get_value(db, "demo_last_event")
        if not stored:
            raise webhook.WebhookRejected(409, "No simulated event to replay yet.")
        body = stored.encode()
    else:
        rng = random.Random()
        max_id = db.scalar(select(func.max(Order.woo_order_id)).where(Order.source == SOURCE_DEMO)) or 1000
        candidates = db.scalars(select(Customer).where(
            Customer.source == SOURCE_DEMO, Customer.is_guest.is_(False))).all()
        cust = rng.choice(candidates) if candidates else None  # portable across SQLite/MySQL/Postgres
        if not cust:
            raise webhook.WebhookRejected(409, "Load demo data first.")
        first, _, last = cust.name.partition(" ")
        raw = _raw_order(max_id + 1, cust.woo_customer_id, first, last, cust.email, "completed", utcnow(), rng)
        body = json.dumps(raw).encode()
        set_value(db, "demo_last_event", body.decode())
        db.commit()
    sig = webhook.compute_signature(settings.webhook_secret, body) if settings.webhook_secret else ""
    return webhook.handle_webhook(db, body, sig, "order.updated", "demo-simulated", SOURCE_DEMO)
