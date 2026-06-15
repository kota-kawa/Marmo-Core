"""
test_shiprocket.py
------------------
Smoke-test Shiprocket API credentials and core endpoints.

    export SHIPROCKET_EMAIL=your_api_user@email.com
    export SHIPROCKET_PASSWORD=your_api_password
    python test_shiprocket.py
"""

import os, sys
from shiprocket_client import ShiprocketClient

if not os.environ.get("SHIPROCKET_EMAIL"):
    print("ERROR: Set SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD env vars.")
    sys.exit(1)

sr = ShiprocketClient()

# Test 1 — Token
print("\n=== Test 1: Auth Token ===")
_ = sr.headers
print("✅ Token OK")

# Test 2 — Serviceability
print("\n=== Test 2: Serviceability (Delhi → Mumbai) ===")
couriers = sr.check_serviceability("110001", "400001", weight=0.5)
for c in couriers[:3]:
    print(f"  {c['courier_name']:30s} ₹{c['rate']}")
print(f"✅ {len(couriers)} couriers available")

# Test 3 — Create order (comment out if you don't want a real order created)
print("\n=== Test 3: Create Order (SKIPPED — uncomment to run) ===")
# result = sr.ship_order({
#     "order_id":              "TEST-001",
#     "order_date":            "2025-04-25 12:00",
#     "pickup_location":       "Primary",
#     "billing_customer_name": "Test User",
#     "billing_last_name":     "User",
#     "billing_address":       "123 Test Street",
#     "billing_city":          "Mumbai",
#     "billing_pincode":       "400001",
#     "billing_state":         "Maharashtra",
#     "billing_country":       "India",
#     "billing_email":         "test@example.com",
#     "billing_phone":         "9000000000",
#     "shipping_is_billing":   True,
#     "order_items": [{
#         "name": "Test Item", "sku": "TEST-SKU",
#         "units": 1, "selling_price": 299,
#         "discount": "", "tax": "", "hsn": 441122
#     }],
#     "payment_method": "Prepaid",
#     "sub_total": 299,
#     "length": 20, "breadth": 15, "height": 5, "weight": 0.3
# }, pickup_pin="110001", delivery_pin="400001")
# print(result)

print("\n✅ All tests passed.")
