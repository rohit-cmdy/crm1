from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import webhook

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/woocommerce")
async def woocommerce_webhook(
        request: Request, db: Session = Depends(get_db),
        x_wc_webhook_signature: Optional[str] = Header(None),
        x_wc_webhook_topic: Optional[str] = Header(None),
        x_wc_webhook_delivery_id: Optional[str] = Header(None)):
    raw = await request.body()  # original bytes: the signature is computed over exactly these
    if len(raw) > 2_000_000:
        raise HTTPException(413, "Payload too large.")
    try:
        return webhook.handle_webhook(db, raw, x_wc_webhook_signature or "", x_wc_webhook_topic,
                                      x_wc_webhook_delivery_id)
    except webhook.WebhookRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
