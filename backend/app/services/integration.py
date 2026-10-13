from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import SyncLog
from .app_settings import get_mode, source_for


def build_status(db: Session) -> dict:
    mode = get_mode(db)
    source = source_for(mode)
    base = select(SyncLog).where(SyncLog.source == source)
    last_ok = db.scalar(select(func.max(SyncLog.created_at)).where(
        SyncLog.source == source, SyncLog.entity_type == "sync", SyncLog.status == "success"))
    failures = db.scalar(select(func.count(SyncLog.id)).where(
        SyncLog.source == source, SyncLog.status == "error")) or 0
    last_err = db.scalar(base.where(SyncLog.status == "error").order_by(SyncLog.created_at.desc()).limit(1))
    if mode == "demo":
        state = "demo"
    elif not settings.woo_configured:
        state = "not_configured"
    elif last_err and (not last_ok or last_err.created_at > last_ok):
        state = "error"
    elif last_ok:
        state = "connected"
    else:
        state = "not_synced"
    return {
        "mode": mode, "state": state, "configured": settings.woo_configured,
        "store_host": settings.store_host, "last_sync_at": last_ok, "failure_count": failures,
        "last_error": last_err.error_summary if last_err else None,
        "last_error_at": last_err.created_at if last_err else None,
        "webhook_secret_configured": bool(settings.webhook_secret),
        "event_rule": {"order_statuses": settings.followup_statuses,
                       "due_in_days": settings.followup_due_days},
        "sync_limit_per_resource": settings.sync_per_page * settings.sync_max_pages,
    }
