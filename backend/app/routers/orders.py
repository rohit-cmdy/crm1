from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import Customer, Order, OrderItem
from .common import current_source, like_escape

router = APIRouter(prefix="/api/orders", tags=["orders"])


def order_query(source):
    items = (select(OrderItem.order_id.label("oid"), func.count(OrderItem.id).label("n"))
             .group_by(OrderItem.order_id).subquery())
    return (select(Order, Customer.name, Customer.is_guest, items.c.n)
            .outerjoin(Customer, Customer.id == Order.customer_id)
            .outerjoin(items, items.c.oid == Order.id).where(Order.source == source))


def row_to_order(row, cls=schemas.OrderOut, **extra):
    o, cname, is_guest, n = row
    return cls(
        id=o.id, source=o.source, woo_order_id=o.woo_order_id, order_number=o.order_number,
        status=o.status, total=o.total, currency=o.currency, order_date=o.order_date,
        customer_id=o.customer_id, customer_name=cname or o.billing_name,
        billing_email=o.billing_email, is_guest=bool(is_guest) if o.customer_id else True,
        item_count=n or 0, last_synced_at=o.last_synced_at, **extra)


@router.get("", response_model=schemas.Page[schemas.OrderOut])
def list_orders(q: Optional[str] = Query(None, max_length=100), status: Optional[str] = Query(None, max_length=32),
                page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), source: str = Depends(current_source)):
    stmt = order_query(source)
    if status:
        stmt = stmt.where(Order.status == status.lower())
    if q and q.strip():
        pat = f"%{like_escape(q.strip().lstrip('#'))}%"
        stmt = stmt.where(or_(Order.order_number.ilike(pat, escape="\\"),
                              Customer.name.ilike(pat, escape="\\"),
                              Order.billing_name.ilike(pat, escape="\\"),
                              Order.billing_email.ilike(pat, escape="\\")))
    total = db.scalar(select(func.count()).select_from(stmt.with_only_columns(Order.id).subquery()))
    rows = db.execute(stmt.order_by(Order.order_date.desc(), Order.id.desc())
                      .limit(page_size).offset((page - 1) * page_size)).all()
    return {"items": [row_to_order(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{order_id}", response_model=schemas.OrderDetail)
def get_order(order_id: int, db: Session = Depends(get_db), source: str = Depends(current_source)):
    row = db.execute(order_query(source).where(Order.id == order_id)
                     .options(selectinload(Order.items))).first()
    if not row:
        raise HTTPException(404, "Order not found in the current mode.")
    return row_to_order(row, schemas.OrderDetail, items=list(row[0].items))
