from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Customer, Interaction, Order
from ..services import workflow
from .common import current_source, get_customer_or_404, like_escape
from .orders import order_query, row_to_order

router = APIRouter(prefix="/api/customers", tags=["customers"])
EXCLUDED = ("cancelled", "failed", "refunded", "trash")


def _stats():
    return (select(
        Order.customer_id.label("cid"),
        func.count(Order.id).label("n"),
        func.coalesce(func.sum(case((Order.status.notin_(EXCLUDED), Order.total), else_=0)), 0).label("spent"),
        func.max(Order.order_date).label("last"),
        func.max(Order.currency).label("cur"),
    ).where(Order.customer_id.is_not(None)).group_by(Order.customer_id).subquery())


def _to_out(cls, row):
    c, n, spent, last, cur = row
    d = {k: getattr(c, k) for k in cls.model_fields if hasattr(c, k)}
    d.update(total_orders=n or 0, total_spent=spent or 0, currency=cur, last_order_date=last)
    return cls(**d)


def _query(source):
    s = _stats()
    return select(Customer, s.c.n, s.c.spent, s.c.last, s.c.cur).outerjoin(
        s, s.c.cid == Customer.id).where(Customer.source == source)


@router.get("", response_model=schemas.Page[schemas.CustomerOut])
def list_customers(q: Optional[str] = Query(None, max_length=100), page: int = Query(1, ge=1),
                   page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
                   source: str = Depends(current_source)):
    stmt = _query(source)
    if q and q.strip():
        pat = f"%{like_escape(q.strip())}%"
        stmt = stmt.where(or_(Customer.name.ilike(pat, escape="\\"), Customer.email.ilike(pat, escape="\\")))
    total = db.scalar(select(func.count()).select_from(stmt.with_only_columns(Customer.id).subquery()))
    rows = db.execute(stmt.order_by(Customer.name, Customer.id)
                      .limit(page_size).offset((page - 1) * page_size)).all()
    return {"items": [_to_out(schemas.CustomerOut, r) for r in rows],
            "total": total, "page": page, "page_size": page_size}


@router.get("/{customer_id}", response_model=schemas.CustomerDetail)
def get_customer(customer_id: int, db: Session = Depends(get_db), source: str = Depends(current_source)):
    get_customer_or_404(db, customer_id, source)
    row = db.execute(_query(source).where(Customer.id == customer_id)).one()
    return _to_out(schemas.CustomerDetail, row)


@router.get("/{customer_id}/orders", response_model=List[schemas.OrderOut])
def customer_orders(customer_id: int, db: Session = Depends(get_db), source: str = Depends(current_source)):
    get_customer_or_404(db, customer_id, source)
    rows = db.execute(order_query(source).where(Order.customer_id == customer_id)
                      .order_by(Order.order_date.desc()).limit(200)).all()
    return [row_to_order(r) for r in rows]


@router.get("/{customer_id}/interactions", response_model=List[schemas.InteractionOut])
def list_interactions(customer_id: int, db: Session = Depends(get_db), source: str = Depends(current_source)):
    get_customer_or_404(db, customer_id, source)
    return db.scalars(select(Interaction).where(Interaction.customer_id == customer_id)
                      .order_by(Interaction.created_at.desc(), Interaction.id.desc()).limit(200)).all()


@router.post("/{customer_id}/interactions", response_model=schemas.InteractionOut, status_code=201)
def add_interaction(customer_id: int, body: schemas.InteractionCreate, db: Session = Depends(get_db),
                    source: str = Depends(current_source)):
    get_customer_or_404(db, customer_id, source)
    item = Interaction(customer_id=customer_id, type=body.type, summary=body.summary)
    db.add(item)
    db.commit()
    return item


@router.get("/{customer_id}/message-template", response_model=schemas.MessageTemplateOut)
def message_template(customer_id: int, order_id: Optional[int] = None, db: Session = Depends(get_db),
                     source: str = Depends(current_source)):
    customer = get_customer_or_404(db, customer_id, source)
    order = None
    if order_id is not None:
        order = db.get(Order, order_id)
        if not order or order.customer_id != customer_id:
            from fastapi import HTTPException
            raise HTTPException(404, "Order not found for this customer.")
    return workflow.render_template(customer, order)
