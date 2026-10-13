from sqlalchemy.orm import Session

from ..config import settings
from ..models import SOURCE_DEMO, SOURCE_REAL, AppSetting


def get_mode(db: Session) -> str:
    row = db.get(AppSetting, "mode")
    if row and row.value in ("real", "demo"):
        return row.value
    return "demo" if settings.demo_mode else "real"


def set_mode(db: Session, mode: str) -> None:
    row = db.get(AppSetting, "mode")
    if row:
        row.value = mode
    else:
        db.add(AppSetting(key="mode", value=mode))
    db.commit()


def source_for(mode: str) -> str:
    return SOURCE_DEMO if mode == "demo" else SOURCE_REAL


def get_value(db, key, default=None):
    row = db.get(AppSetting, key)
    return row.value if row else default


def set_value(db, key, value):
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
