# Shiprocket API — Endpoint Reference
# Base: https://apiv2.shiprocket.in/v1/external/
# Auth: Bearer token in Authorization header (all endpoints)
# Source: https://apidocs.shiprocket.in/

## Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/login | Get JWT token (valid 24 hrs) |

## Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /orders/create/adhoc | Create a new order |
| GET  | /orders/show/{order_id} | Fetch single order |
| GET  | /orders | List all orders |
| POST | /orders/cancel | Cancel orders by IDs |
| POST | /orders/update/pickup | Update pickup location |
| POST | /orders/address/update | Update customer address |

## Courier & AWB
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /courier/serviceability/ | Check serviceability + rates |
| POST | /courier/assign/awb | Assign courier, generate AWB |
| POST | /courier/generate/pickup | Request pickup |
| POST | /courier/generate/label | Generate shipping label (PDF) |
| GET  | /courier/courierListWithCounts | List all couriers |

## Tracking
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /courier/track/awb/{awb} | Track by AWB |
| GET | /courier/track/order/{order_id} | Track by order ID |
| GET | /courier/track?awb=A,B,C | Batch track multiple AWBs |

## Shipments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /shipments | List all shipments |
| GET  | /shipments/{shipment_id} | Fetch specific shipment |

## NDR (Non-Delivery Reports)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /ndr/all | All NDR shipments |
| GET  | /ndr/{awb} | Specific AWB in NDR |
| POST | /ndr/reattempt | Re-attempt delivery |
| POST | /ndr/return | Initiate return |

## Manifest
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /manifests/generate | Generate manifest for courier pickup |
| POST | /manifests/print | Print manifest PDF |

## Returns
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /orders/return | Create return order |
| GET  | /orders/return | List return orders |

## Wallet / Billing
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /account/details/wallet-balance | Check wallet balance |

---

## Key Field Notes

**payment_method:** `"Prepaid"` | `"COD"` (case-sensitive)

**order_date format:** `"YYYY-MM-DD HH:MM"` e.g. `"2025-04-25 14:30"`

**weight:** in kg (e.g. `0.5` for 500g)

**dimensions:** length, breadth, height in cm

**shipping_is_billing:** set `true` if shipping address = billing address

**hsn:** HSN code for item (required for GST, e.g. `441122` for paper goods, `620469` for apparel)
