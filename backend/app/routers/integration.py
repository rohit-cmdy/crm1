from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..database import get_db
from ..models import SOURCE_DEMO
from ..services import demo, sync, webhook
from ..services.app_settings import get_mode, set_mode
from ..services.integration import build_status
from ..services.woo_client import WooError

router = APIRouter(prefix="/api/integrations", tags=["integration"])


def _require_real(db):
    if get_mode(db) == "demo":
        raise HTTPException(409, "The app is in demo mode. Switch to real mode to use WooCommerce.")
    if not settings.woo_configured:
        raise HTTPException(400, "WooCommerce is not configured. Set WOOCOMMERCE_STORE_URL, "
                                 "WOOCOMMERCE_CONSUMER_KEY and WOOCOMMERCE_CONSUMER_SECRET in .env and restart.")


@router.get("/woocommerce/status")
def status(db: Session = Depends(get_db)):
    return jsonable_encoder(build_status(db))


@router.post("/woocommerce/test")
def test_connection(db: Session = Depends(get_db)):
    _require_real(db)
    try:
        totals = sync.build_client().check_access()
    except WooError as exc:
        raise HTTPException(502, exc.message)
    return {"status": "ok", "message": "Credentials can read customers and orders.", "totals_in_store": totals}


@router.post("/woocommerce/sync")
def run_sync(db: Session = Depends(get_db)):
    _require_real(db)
    try:
        return sync.sync_woocommerce(db)
    except WooError as exc:
        raise HTTPException(502, exc.message)


@router.post("/mode")
def change_mode(body: schemas.ModeUpdate, db: Session = Depends(get_db)):
    set_mode(db, body.mode)
    return jsonable_encoder(build_status(db))


@router.post("/demo/seed")
def seed(db: Session = Depends(get_db)):
    if get_mode(db) != "demo":
        raise HTTPException(409, "Switch to demo mode before loading sample data.")
    return {"status": "ok", **demo.seed_demo(db)}


@router.post("/demo/simulate-order")
def simulate(replay: bool = False, db: Session = Depends(get_db)):
    if get_mode(db) != "demo":
        raise HTTPException(409, "Simulated events are only available in demo mode.")
    try:
        return demo.simulate_order_event(db, replay=replay)
    except webhook.WebhookRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
