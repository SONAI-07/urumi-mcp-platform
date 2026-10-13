import os
import json
from mcp.server.fastmcp import FastMCP
import woo_client

# Initialize the MCP server with a name
mcp = FastMCP("WooCommerce-MCP", host="0.0.0.0", port=8000)

# --- TOOL 1: List Products ---
@mcp.tool()
def list_products(limit: int = 20) -> str:
    """List products from the WooCommerce store."""
    products = woo_client.list_products(limit=limit)

    # Return a summarized JSON to save LLM context tokens

    summary = [
        {"id": p["id"], "name": p["name"], "price": p["price"], "status": p["status"]}
        for p in products
    ]
    return json.dumps(summary)

# --- TOOL 2: Create Product ---
@mcp.tool()
def create_product(name: str, price: str, description: str = "") -> str:
    """Create a new product in the WooCommerce store."""
    product = woo_client.create_product(name, price, description)
    return json.dumps({
        "success": True,
        "id": product["id"],
        "permalink": product["permalink"]
    })

# --- TOOL 3: List Orders ---
@mcp.tool()
def list_orders(limit: int = 20) -> str:
    """List recent orders from the WooCommerce store."""
    orders = woo_client.list_orders(limit=limit)
    summary = [
        {
            "id": o["id"],
            "status": o["status"],
            "total": o["total"],
            "date_created": o["date_created"],
            "billing_name": f"{o['billing']['first_name']} {o['billing']['last_name']}"
        }
        for o in orders
    ]
    return json.dumps(summary)

# --- TOOL 4: Get Order ---
@mcp.tool()
def get_order(order_id: int) -> str:
    """Get detailed information about a specific order by its ID."""
    order = woo_client.get_order(order_id)
    return json.dumps(order)

# --- TOOL 5: Update Order Status ---
@mcp.tool()
def update_order_status(order_id: int, status: str) -> str:
    """Update the status of an order. Valid statuses: pending, processing, on-hold, completed, cancelled, refunded, failed."""
    order = woo_client.update_order_status(order_id, status)
    return json.dumps({
        "success": True,
        "id": order["id"],
        "new_status": order["status"]
    })

if __name__ == "__main__":
    # Run the server using Streamable HTTP transport as strictly required by the assignment
    # This will start a server on http://localhost:8000/mcp by default
    print("Starting WooCommerce MCP Server on http://localhost:8000/mcp ...")
    mcp.run(transport="streamable-http")