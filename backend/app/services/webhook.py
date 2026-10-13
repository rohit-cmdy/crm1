"""WooCommerce webhook processing: signature check on the raw body, idempotency, reconcile."""
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SOURCE_REAL, WebhookEvent, utcnow
from . import sync, workflow

log = logging.getLogger("crm.webhook")


class WebhookRejected(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def compute_signature(secret: str, raw_body: bytes) -> str:
    return base64.b64encode(hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()).decode()


def verify_signature(secret: str, raw_body: bytes, header: str) -> bool:
    if not secret or not header:
        return False
    return hmac.compare_digest(compute_signature(secret, raw_body), header.strip())


def handle_webhook(db: Session, raw_body: bytes, signature: str, topic: str = None,
                   delivery_id: str = None, source: str = SOURCE_REAL) -> dict:
    if not settings.webhook_secret:
        raise WebhookRejected(503, "WEBHOOK_SECRET is not configured; webhooks cannot be verified.")
    # 1. Verify against the ORIGINAL raw bytes before touching the payload.
    if not verify_signature(settings.webhook_secret, raw_body, signature):
        sync.record_failure(db, "Webhook rejected: invalid or missing signature", "webhook", delivery_id, source)
        raise WebhookRejected(401, "Invalid webhook signature.")

    # WooCommerce sends a form-encoded "ping" (webhook_id=N) when a webhook is created.
    if raw_body.startswith(b"webhook_id="):
        return {"status": "ping"}

    topic = (topic or "").lower()
    if topic and not topic.startswith("order."):
        return {"status": "ignored", "reason": f"topic '{topic}' is not handled"}

    # 2. Parse safely.
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        data = sync.normalize_order(payload)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        sync.record_failure(db, f"Webhook payload malformed: {exc}", "webhook", delivery_id, source)
        raise WebhookRejected(400, f"Malformed order payload: {exc}")

    # 3. Idempotency: identical body already processed -> acknowledge, change nothing.
    event_hash = hashlib.sha256(raw_body).hexdigest()
    event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_hash == event_hash))
    if event is None:
        event = WebhookEvent(event_hash=event_hash, delivery_id=delivery_id, topic=topic or None)
        db.add(event)
        try:
            db.commit()
        except IntegrityError:  # concurrent identical delivery
            db.rollback()
            event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_hash == event_hash))
    if event.status == "processed":
        return {"status": "duplicate", "order_id": data["woo_order_id"]}

    # 4. Reconcile the order + apply the follow-up rule in one transaction.
    try:
        order, created, previous = sync.upsert_order(db, source, data)
        task = workflow.apply_order_rule(db, source, order)
        event.status, event.error, event.processed_at = "processed", None, utcnow()
        sync._log(db, "success", "webhook", str(data["woo_order_id"]), source=source)
        db.commit()
    except Exception as exc:
        log.exception("webhook processing failed")
        db.rollback()
        event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_hash == event_hash))
        if event:
            event.status, event.error = "error", f"{type(exc).__name__}"
            db.commit()
        sync.record_failure(db, f"Webhook processing failed: {type(exc).__name__}", "webhook",
                            str(data["woo_order_id"]), source)
        raise WebhookRejected(500, "Webhook processing failed; WooCommerce may retry.")
    return {"status": "processed", "order_id": data["woo_order_id"],
            "order_created": created, "previous_status": previous,
            "follow_up_created": task is not None}
