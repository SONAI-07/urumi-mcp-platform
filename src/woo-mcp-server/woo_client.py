import os
import httpx

WOO_URL = os.environ.get("WOO_URL", "http://store.127.0.0.1.nip.io").rstrip("/")
CONSUMER_KEY = os.environ.get("WOO_CONSUMER_KEY", "")
CONSUMER_SECRET = os.environ.get("WOO_CONSUMER_SECRET", "")

if not CONSUMER_KEY or not CONSUMER_SECRET:
    print("⚠️ WARNING: WOO_CONSUMER_KEY or WOO_CONSUMER_SECRET environment variables are missing!")

AUTH_PARAMS = {"consumer_key": CONSUMER_KEY, "consumer_secret": CONSUMER_SECRET}

def _client() -> httpx.Client:
    return httpx.Client(base_url=f"{WOO_URL}/wp-json/wc/v3", timeout=15.0)

def list_products(limit: int = 20) -> list[dict]:
    with _client() as c:
        r = c.get("/products", params={**AUTH_PARAMS, "per_page": limit})
        r.raise_for_status()
        return r.json()

def create_product(name: str, price: str, description: str = "") -> dict:
    with _client() as c:
        r = c.post("/products", params=AUTH_PARAMS,
                   json={"name": name, "regular_price": price,
                         "description": description, "type": "simple"})
        r.raise_for_status()
        return r.json()

def list_orders(limit: int = 20) -> list[dict]:
    with _client() as c:
        r = c.get("/orders", params={**AUTH_PARAMS, "per_page": limit})
        r.raise_for_status()
        return r.json()

def get_order(order_id: int) -> dict:
    with _client() as c:
        r = c.get(f"/orders/{order_id}", params=AUTH_PARAMS)
        r.raise_for_status()
        return r.json()

def update_order_status(order_id: int, status: str) -> dict:
    with _client() as c:
        r = c.put(f"/orders/{order_id}", params=AUTH_PARAMS,
                  json={"status": status})
        r.raise_for_status()
        return r.json()