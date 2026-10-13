from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import customers, followups, integration, orders, system, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="WooCommerce CRM API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type"])

for r in (system, customers, orders, followups, integration, webhooks):
    app.include_router(r.router)
