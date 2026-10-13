"""Environment-driven configuration. Secrets are only ever read from the environment."""
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")  # project-root .env (existing env vars win)


def _bool(value, default=False):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self):
        env = os.environ.get
        self.store_url = (env("WOOCOMMERCE_STORE_URL") or "").strip()
        self.consumer_key = (env("WOOCOMMERCE_CONSUMER_KEY") or "").strip()
        self.consumer_secret = (env("WOOCOMMERCE_CONSUMER_SECRET") or "").strip()
        self.database_url = env("DATABASE_URL") or f"sqlite:///{(BACKEND_DIR / 'crm.db').as_posix()}"
        self.webhook_secret = (env("WEBHOOK_SECRET") or "").strip()
        self.demo_mode = _bool(env("DEMO_MODE"), False)
        self.frontend_origin = (env("FRONTEND_ORIGIN") or "http://localhost:5173").strip()
        # Sync bounds: per_page * max_pages records per resource per sync.
        self.sync_per_page = min(max(_int(env("SYNC_PER_PAGE"), 50), 1), 100)
        self.sync_max_pages = max(_int(env("SYNC_MAX_PAGES"), 5), 1)
        self.request_timeout = _int(env("WOOCOMMERCE_TIMEOUT_SECONDS"), 15)
        # Event rule: which order statuses create a follow-up task, and when it is due.
        statuses = env("FOLLOWUP_ORDER_STATUSES") or "completed"
        self.followup_statuses = [s.strip().lower() for s in statuses.split(",") if s.strip()]
        self.followup_due_days = _int(env("FOLLOWUP_DUE_DAYS"), 3)

    @property
    def woo_configured(self):
        return bool(self.store_url and self.consumer_key and self.consumer_secret)

    @property
    def store_host(self):
        return urlparse(self.store_url).netloc if self.store_url else None


settings = Settings()
