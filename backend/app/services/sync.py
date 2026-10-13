"""Normalisation + idempotent upsert of WooCommerce customers/orders, and the sync job."""
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SOURCE_REAL, Customer, Order, OrderItem, SyncLog, utcnow
from .woo_client import WooClient, WooError

log = logging.getLogger("crm.sync")
logging.getLogger("httpx").setLevel(logging.WARNING)  # never log request URLs


def build_client() -> WooClient:
    return WooClient(settings.store_url, settings.consumer_key, settings.consumer_secret,
                     timeout=settings.request_timeout)


# ---------- normalisation (pure functions; raise ValueError on bad data) ----------

def _dec(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"invalid number {value!r}")


def _dt(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"invalid date {value!r}")
    return d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def _s(value, limit=255):
    value = (str(value).strip() if value is not None else "")
    return value[:limit] or None


def _full_name(first, last):
    return " ".join(p for p in ((first or "").strip(), (last or "").strip()) if p)


def normalize_customer(raw: dict) -> dict:
    if not isinstance(raw, dict) or not raw.get("id"):
        raise ValueError("customer has no id")
    billing = raw.get("billing") or {}
    email = _s(raw.get("email") or billing.get("email"))
    name = (_full_name(raw.get("first_name"), raw.get("last_name"))
            or _full_name(billing.get("first_name"), billing.get("last_name"))
            or raw.get("username") or (email or "").split("@")[0] or f"Customer {raw['id']}")
    return {
        "woo_customer_id": int(raw["id"]), "name": name[:255],
        "email": email.lower() if email else None, "phone": _s(billing.get("phone"), 64),
        "address_line": _s(billing.get("address_1")), "city": _s(billing.get("city"), 120),
        "state": _s(billing.get("state"), 120), "postcode": _s(billing.get("postcode"), 32),
        "country": _s(billing.get("country"), 8),
    }


def normalize_order(raw: dict) -> dict:
    if not isinstance(raw, dict) or not raw.get("id"):
        raise ValueError("order has no id")
    status = raw.get("status")
    if not isinstance(status, str) or not status:
        raise ValueError("order has no status")
    billing = raw.get("billing") or {}
    email = _s(billing.get("email"))
    items = []
    for li in raw.get("line_items") or []:
        qty = int(li.get("quantity") or 1)
        if li.get("price") not in (None, ""):
            unit = _dec(li["price"])
        else:
            unit = (_dec(li.get("subtotal")) / qty) if qty else Decimal("0")
        items.append({"woo_product_id": li.get("product_id") or None,
                      "name": (_s(li.get("name")) or "Unnamed product"),
                      "quantity": qty, "unit_price": unit.quantize(Decimal("0.01"))})
    contact = {k: _s(billing.get(k), n) for k, n in
               (("phone", 64), ("address_1", 255), ("city", 120), ("state", 120),
                ("postcode", 32), ("country", 8))}
    return {
        "woo_order_id": int(raw["id"]),
        "order_number": str(raw.get("number") or raw["id"])[:64],
        "status": status.lower()[:32],
        "total": _dec(raw.get("total")),
        "currency": (_s(raw.get("currency"), 8) or ""),
        "order_date": _dt(raw.get("date_created_gmt") or raw.get("date_created")),
        "woo_customer_id": int(raw.get("customer_id") or 0),
        "billing_name": _full_name(billing.get("first_name"), billing.get("last_name")) or None,
        "billing_email": email.lower() if email else None,
        "billing": contact,
        "items": items,
    }


# ---------- upserts ----------

def upsert_customer(db: Session, source: str, c: dict):
    cust = None
    if c.get("woo_customer_id"):
        cust = db.scalar(select(Customer).where(
            Customer.source == source, Customer.woo_customer_id == c["woo_customer_id"]))
    if cust is None and c.get("email"):
        cust = db.scalar(select(Customer).where(
            Customer.source == source, Customer.email == c["email"]))
    created = cust is None
    if created:
        cust = Customer(source=source, name=c.get("name") or "Guest")
        db.add(cust)
    if c.get("woo_customer_id"):
        cust.woo_customer_id = c["woo_customer_id"]
        cust.is_guest = False
    elif created:
        cust.is_guest = True
    # WooCommerce owns contact data: overwrite with non-empty synced values only,
    # so an incomplete payload can never blank out valid existing data.
    for field in ("name", "email", "phone", "address_line", "city", "state", "postcode", "country"):
        if c.get(field):
            setattr(cust, field, c[field])
    db.flush()
    return cust, created


def upsert_order(db: Session, source: str, o: dict):
    """Returns (order, created, previous_status)."""
    customer = None
    if o["woo_customer_id"] > 0:
        b = o["billing"]
        customer, _ = upsert_customer(db, source, {
            "woo_customer_id": o["woo_customer_id"], "name": o["billing_name"],
            "email": o["billing_email"], "phone": b.get("phone"),
            "address_line": b.get("address_1"), "city": b.get("city"), "state": b.get("state"),
            "postcode": b.get("postcode"), "country": b.get("country")})
    elif o["billing_email"]:
        b = o["billing"]
        customer, _ = upsert_customer(db, source, {
            "woo_customer_id": None,
            "name": o["billing_name"] or o["billing_email"].split("@")[0],
            "email": o["billing_email"], "phone": b.get("phone")})
    # Guest orders with no email keep only the order-level contact snapshot.

    order = db.scalar(select(Order).where(Order.source == source,
                                          Order.woo_order_id == o["woo_order_id"]))
    created = order is None
    previous_status = None if created else order.status
    if created:
        order = Order(source=source, woo_order_id=o["woo_order_id"])
        db.add(order)
    order.customer_id = customer.id if customer else None
    order.order_number = o["order_number"]
    order.status = o["status"]
    order.total = o["total"]
    order.currency = o["currency"]
    order.order_date = o["order_date"]
    order.billing_name = o["billing_name"]
    order.billing_email = o["billing_email"]
    order.last_synced_at = utcnow()
    order.items.clear()
    for it in o["items"]:
        order.items.append(OrderItem(**it))
    db.flush()
    return order, created, previous_status


# ---------- sync job ----------

def _log(db, status, entity="sync", external_id=None, error=None, source=SOURCE_REAL):
    db.add(SyncLog(source=source, entity_type=entity, external_id=external_id,
                   status=status, error_summary=error))


def record_failure(db: Session, message: str, entity="sync", external_id=None, source=SOURCE_REAL):
    db.rollback()
    _log(db, "error", entity, external_id, message[:1000], source)
    db.commit()


def sync_woocommerce(db: Session, client: WooClient = None) -> dict:
    """Pull customers + orders (bounded), upsert by WooCommerce ID, log the outcome.
    Nothing is written unless every page was fetched successfully."""
    client = client or build_client()
    per_page, max_pages = settings.sync_per_page, settings.sync_max_pages
    try:
        client.check_access()
        raw_customers, cust_trunc, cust_total = client.paginate(
            "customers", per_page, max_pages, role="all", orderby="registered_date", order="desc")
        raw_orders, ord_trunc, ord_total = client.paginate(
            "orders", per_page, max_pages, orderby="date", order="desc")
    except WooError as exc:
        record_failure(db, exc.message)
        raise

    stats = {"customers": {"created": 0, "updated": 0, "skipped": 0},
             "orders": {"created": 0, "updated": 0, "skipped": 0}}
    try:
        for raw in raw_customers:
            try:
                data = normalize_customer(raw)
            except (ValueError, TypeError) as exc:
                stats["customers"]["skipped"] += 1
                _log(db, "skipped", "customer", str((raw or {}).get("id") if isinstance(raw, dict) else None), str(exc))
                continue
            _, created = upsert_customer(db, SOURCE_REAL, data)
            stats["customers"]["created" if created else "updated"] += 1
        for raw in raw_orders:
            try:
                data = normalize_order(raw)
            except (ValueError, TypeError) as exc:
                stats["orders"]["skipped"] += 1
                _log(db, "skipped", "order", str((raw or {}).get("id") if isinstance(raw, dict) else None), str(exc))
                continue
            _, created, _ = upsert_order(db, SOURCE_REAL, data)
            stats["orders"]["created" if created else "updated"] += 1
        _log(db, "success")
        db.commit()
    except Exception as exc:  # DB error: nothing partial is kept
        log.exception("sync failed while saving")
        record_failure(db, f"Saving synchronized data failed: {type(exc).__name__}")
        raise WooError("Synchronization fetched data but could not save it. See sync log.") from exc

    return {"status": "success", "stats": stats,
            "truncated": cust_trunc or ord_trunc,
            "totals_in_store": {"customers": cust_total, "orders": ord_total},
            "limit_per_resource": per_page * max_pages}
