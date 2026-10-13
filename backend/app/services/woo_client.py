"""Thin WooCommerce REST API v3 client (read-only)."""
from urllib.parse import urlparse

import httpx

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_SUFFIXES = (".local", ".test", ".localhost")


class WooError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_store_url(url: str) -> str:
    if not url:
        raise WooError("WOOCOMMERCE_STORE_URL is not set.")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise WooError("Store URL must look like https://your-store.com")
    if parsed.username or parsed.password:
        raise WooError("Store URL must not contain credentials.")
    host = parsed.hostname.lower()
    is_local = host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES)
    if parsed.scheme == "http" and not is_local:
        raise WooError("Store URL must use HTTPS so API credentials are not sent in clear text.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


class WooClient:
    def __init__(self, store_url, consumer_key, consumer_secret, timeout=15, transport=None):
        if not consumer_key or not consumer_secret:
            raise WooError("WooCommerce consumer key and secret are not set.")
        self.base = validate_store_url(store_url) + "/wp-json/wc/v3"
        self._auth = (consumer_key, consumer_secret)
        self.timeout = timeout
        self.transport = transport

    def get_page(self, resource, page=1, per_page=50, **params):
        """Returns (items, total_pages, total_items)."""
        url = f"{self.base}/{resource}"
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport, auth=self._auth,
                              headers={"Accept": "application/json"}) as http:
                resp = http.get(url, params={"page": page, "per_page": per_page, **params})
        except httpx.TimeoutException:
            raise WooError(f"The store did not respond within {self.timeout}s.")
        except httpx.ConnectError:
            raise WooError("Could not connect to the store. Check the URL, DNS and that the site is online.")
        except httpx.HTTPError as exc:
            raise WooError(f"Request to the store failed ({type(exc).__name__}).")

        code = resp.status_code
        if code in (401, 403):
            raise WooError(f"WooCommerce rejected the API credentials (HTTP {code}). "
                           "Check the key/secret and that the key has Read permission.", code)
        if code == 404:
            raise WooError("WooCommerce REST API not found (HTTP 404). Check the store URL and "
                           "that WooCommerce is active with pretty permalinks enabled.", code)
        if 300 <= code < 400:
            raise WooError(f"The store URL redirects (HTTP {code}). Use the final https:// address.", code)
        if code >= 400:
            raise WooError(f"WooCommerce returned HTTP {code}.", code)
        try:
            data = resp.json()
        except ValueError:
            raise WooError("The store did not return JSON. Is this a WooCommerce site?", code)
        if not isinstance(data, list):
            raise WooError("Unexpected response from WooCommerce (expected a list).", code)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1) or 1)
        total_items = int(resp.headers.get("X-WP-Total", len(data)) or 0)
        return data, total_pages, total_items

    def paginate(self, resource, per_page, max_pages, **params):
        """Fetch up to max_pages pages. Returns (items, truncated, total_items)."""
        items, page, total_items = [], 1, 0
        while True:
            batch, total_pages, total_items = self.get_page(resource, page, per_page, **params)
            items.extend(batch)
            if page >= total_pages or not batch:
                return items, False, total_items
            if page >= max_pages:
                return items, True, total_items
            page += 1

    def check_access(self):
        """Verify the credentials can read the resources the CRM needs."""
        totals = {}
        for resource in ("customers", "orders"):
            _, _, total = self.get_page(resource, 1, 1)
            totals[resource] = total
        return totals
