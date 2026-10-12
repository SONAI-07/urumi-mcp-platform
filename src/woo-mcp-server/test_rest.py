import woo_client as woo

print("--- Starting WooCommerce Connection Test ---")

try:
    products = woo.list_products()
    print(f"✅ Products found ({len(products)}):")
    for p in products:
        print(f"  - [{p['id']}] {p['name']} - ${p['price']}")

    orders = woo.list_orders()
    print(f"✅ Orders found ({len(orders)}):")
    for o in orders:
        print(
            f"  - [{o['id']}] Status: {o['status']} | Customer: {o['billing']['first_name']} {o['billing']['last_name']}")

except Exception as e:
    print(f"❌ ERROR: {e}")
