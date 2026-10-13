from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Customer, Interaction, Order
from ..services.integration import build_status
from .common import current_source
from .customers import EXCLUDED
from .orders import order_query, row_to_order

router = APIRouter(prefix="/api", tags=["system"])
AWAITING = ("pending", "processing", "on-hold")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@router.get("/dashboard/summary")
def dashboard(db: Session = Depends(get_db), source: str = Depends(current_source)):
    total_customers = db.scalar(select(func.count(Customer.id)).where(Customer.source == source))
    total_orders = db.scalar(select(func.count(Order.id)).where(Order.source == source))
    value = db.execute(select(Order.currency, func.sum(Order.total)).where(
        Order.source == source, Order.status.notin_(EXCLUDED)).group_by(Order.currency)).all()
    by_status = dict(db.execute(select(Order.status, func.count(Order.id)).where(
        Order.source == source).group_by(Order.status)).all())
    recent = db.execute(order_query(source).order_by(Order.order_date.desc(), Order.id.desc()).limit(6)).all()
    activity = db.execute(
        select(Interaction, Customer).join(Customer, Customer.id == Interaction.customer_id)
        .where(Customer.source == source).order_by(Interaction.created_at.desc(), Interaction.id.desc()).limit(8)).all()
    return {
        "total_customers": total_customers, "total_orders": total_orders,
        "order_value": [{"currency": c or "", "total": f"{t:.2f}"} for c, t in value],
        "awaiting_processing": sum(n for s, n in by_status.items() if s in AWAITING),
        "orders_by_status": by_status,
        "recent_orders": [row_to_order(r).model_dump(mode="json") for r in recent],
        "recent_activity": [{"id": i.id, "customer_id": c.id, "customer_name": c.name, "type": i.type,
                             "summary": i.summary,
                             "created_at": schemas.InteractionOut.model_validate(i).model_dump(mode="json")["created_at"]}
                            for i, c in activity],
        "integration": jsonable(build_status(db)),
    }


def jsonable(d):
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(d)
