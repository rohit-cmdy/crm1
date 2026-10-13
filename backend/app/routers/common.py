from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer
from ..services.app_settings import get_mode, source_for


def current_source(db: Session = Depends(get_db)) -> str:
    return source_for(get_mode(db))


def get_customer_or_404(db: Session, customer_id: int, source: str) -> Customer:
    c = db.get(Customer, customer_id)
    if not c or c.source != source:
        raise HTTPException(404, "Customer not found in the current mode.")
    return c


def like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
