"""Official WooCommerce REST API client."""
import os
from woocommerce import API

WOO_URL = os.environ["WOO_URL"]
CONSUMER_KEY = os.environ["WOO_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["WOO_CONSUMER_SECRET"]

# The official SDK automatically handles OAuth 1.0a signatures for HTTP connections!
wcapi = API(
    url=WOO_URL,
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    version="wc/v3",
    timeout=15
)

def list_products(limit: int = 20) -> list[dict]:
    r = wcapi.get("products", params={"per_page": limit})
    r.raise_for_status()
    return r.json()

def create_product(name: str, price: str, description: str = "") -> dict:
    data = {
        "name": name,
        "regular_price": price,
        "description": description,
        "type": "simple"
    }
    r = wcapi.post("products", data=data)
    r.raise_for_status()
    return r.json()

def list_orders(limit: int = 20) -> list[dict]:
    r = wcapi.get("orders", params={"per_page": limit})
    r.raise_for_status()
    return r.json()

def get_order(order_id: int) -> dict:
    r = wcapi.get(f"orders/{order_id}")
    r.raise_for_status()
    return r.json()

def update_order_status(order_id: int, status: str) -> dict:
    r = wcapi.put(f"orders/{order_id}", data={"status": status})
    r.raise_for_status()
    return r.json()