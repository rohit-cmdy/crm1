from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Customer, FollowUpTask, Order, utcnow
from .common import current_source, get_customer_or_404

router = APIRouter(prefix="/api/follow-ups", tags=["follow-ups"])


def to_out(task, customer, order):
    return schemas.FollowUpOut(
        id=task.id, customer_id=task.customer_id, customer_name=customer.name,
        order_id=task.order_id, order_number=order.order_number if order else None,
        title=task.title, due_date=task.due_date, status=task.status,
        automatic=task.external_event_id is not None, created_at=task.created_at,
        completed_at=task.completed_at)


def _base(source):
    return (select(FollowUpTask, Customer, Order).join(Customer, Customer.id == FollowUpTask.customer_id)
            .outerjoin(Order, Order.id == FollowUpTask.order_id).where(Customer.source == source))


@router.get("", response_model=List[schemas.FollowUpOut])
def list_follow_ups(status: Optional[str] = Query(None, pattern="^(pending|completed)$"),
                    customer_id: Optional[int] = None, limit: int = Query(200, ge=1, le=500),
                    db: Session = Depends(get_db), source: str = Depends(current_source)):
    stmt = _base(source)
    if status:
        stmt = stmt.where(FollowUpTask.status == status)
    if customer_id:
        stmt = stmt.where(FollowUpTask.customer_id == customer_id)
    stmt = stmt.order_by(FollowUpTask.due_date.asc(), FollowUpTask.id.desc()).limit(limit)
    return [to_out(*r) for r in db.execute(stmt).all()]


@router.post("", response_model=schemas.FollowUpOut, status_code=201)
def create_follow_up(body: schemas.FollowUpCreate, db: Session = Depends(get_db),
                     source: str = Depends(current_source)):
    customer = get_customer_or_404(db, body.customer_id, source)
    task = FollowUpTask(customer_id=customer.id, title=body.title, due_date=body.due_date)
    db.add(task)
    db.commit()
    return to_out(task, customer, None)


@router.patch("/{task_id}", response_model=schemas.FollowUpOut)
def update_follow_up(task_id: int, body: schemas.FollowUpUpdate, db: Session = Depends(get_db),
                     source: str = Depends(current_source)):
    row = db.execute(_base(source).where(FollowUpTask.id == task_id)).first()
    if not row:
        raise HTTPException(404, "Follow-up not found in the current mode.")
    task, customer, order = row
    task.status = body.status
    task.completed_at = utcnow() if body.status == "completed" else None
    db.commit()
    return to_out(task, customer, order)
