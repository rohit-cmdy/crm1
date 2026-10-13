"""Event rule: an order reaching an eligible status creates ONE follow-up task + activity."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import FollowUpTask, Interaction, Order, utcnow

TEMPLATE_SUBJECT = "Thanks for your order #{order_number}"
TEMPLATE_BODY = (
    "Hi {first_name},\n\n"
    "Thank you for your recent order #{order_number}{items_line}. "
    "We hope everything arrived as expected.\n\n"
    "If you have any questions, or would like help choosing what to try next, "
    "just reply to this message.\n\n"
    "Kind regards,\nThe Customer Care Team"
)


def render_template(customer, order=None) -> dict:
    first = (customer.name or "there").split()[0]
    number, items_line = "", ""
    if order is not None:
        number = order.order_number
        names = [i.name for i in order.items[:2]]
        if names:
            items_line = " (" + ", ".join(names) + (" and more" if len(order.items) > 2 else "") + ")"
    subject = TEMPLATE_SUBJECT.format(order_number=number or "—") if order else "Thanks for your order"
    body = TEMPLATE_BODY.format(first_name=first, order_number=number or "—", items_line=items_line)
    if not order:
        body = body.replace(" #—", "")
    return {"subject": subject, "body": body}


def apply_order_rule(db: Session, source: str, order: Order):
    """Returns the created task, or None (not eligible / guest without profile / duplicate)."""
    if order.status not in settings.followup_statuses or not order.customer_id:
        return None
    event_id = f"{source}:order:{order.woo_order_id}:{order.status}"
    if db.scalar(select(FollowUpTask.id).where(FollowUpTask.external_event_id == event_id)):
        return None
    task = FollowUpTask(
        customer_id=order.customer_id, order_id=order.id,
        title=f"Send post-purchase follow-up for order #{order.order_number}",
        due_date=(utcnow() + timedelta(days=settings.followup_due_days)).date(),
        external_event_id=event_id)
    db.add(task)
    db.add(Interaction(
        customer_id=order.customer_id, type="system",
        summary=f"Order #{order.order_number} is '{order.status}' in WooCommerce. "
                f"Follow-up task created automatically."))
    db.flush()
    return task
