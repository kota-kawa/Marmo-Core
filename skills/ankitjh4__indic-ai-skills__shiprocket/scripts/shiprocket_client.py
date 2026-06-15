"""
shiprocket_client.py
--------------------
Reusable Python client for Shiprocket API.
Base URL: https://apiv2.shiprocket.in/v1/external/
Docs:     https://apidocs.shiprocket.in/

Setup:
    export SHIPROCKET_EMAIL=your_api_user@email.com
    export SHIPROCKET_PASSWORD=your_api_password

Usage:
    from shiprocket_client import ShiprocketClient

    sr = ShiprocketClient()
    couriers   = sr.check_serviceability("110001", "400001", weight=0.5)
    order      = sr.create_order({...})
    awb        = sr.generate_awb(shipment_id, courier_id)
    tracking   = sr.track_by_awb(awb)
"""

import os
import time
import requests


BASE = "https://apiv2.shiprocket.in/v1/external"


class ShiprocketClient:

    def __init__(self, email: str = None, password: str = None):
        self.email    = email    or os.environ["SHIPROCKET_EMAIL"]
        self.password = password or os.environ["SHIPROCKET_PASSWORD"]
        self._token     = None
        self._token_ts  = 0          # unix timestamp when token was fetched
        self.TOKEN_TTL  = 23 * 3600  # refresh 1 hr before 24hr expiry

    # ── Auth ──────────────────────────────────────────────────────────────────

    @property
    def headers(self) -> dict:
        """Auto-refresh token if expired."""
        if not self._token or (time.time() - self._token_ts) > self.TOKEN_TTL:
            self._refresh_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    def _refresh_token(self):
        res = requests.post(f"{BASE}/auth/login", json={
            "email": self.email,
            "password": self.password
        })
        res.raise_for_status()
        self._token    = res.json()["token"]
        self._token_ts = time.time()
        print("Token refreshed.")

    # ── Serviceability ────────────────────────────────────────────────────────

    def check_serviceability(self, pickup_pin: str, delivery_pin: str,
                              weight: float = 0.5, cod: bool = False) -> list:
        """
        Check which couriers can deliver between two pincodes.
        Returns list of available couriers sorted by rate (cheapest first).
        """
        params = {
            "pickup_postcode":   pickup_pin,
            "delivery_postcode": delivery_pin,
            "weight":            weight,
            "cod":               1 if cod else 0
        }
        res = requests.get(f"{BASE}/courier/serviceability/",
                           headers=self.headers, params=params)
        res.raise_for_status()
        couriers = res.json()["data"]["available_courier_companies"]
        return sorted(couriers, key=lambda c: c["rate"])

    def cheapest_courier(self, pickup_pin: str, delivery_pin: str,
                          weight: float = 0.5, cod: bool = False) -> dict:
        """Returns the single cheapest available courier."""
        couriers = self.check_serviceability(pickup_pin, delivery_pin, weight, cod)
        if not couriers:
            raise ValueError("No couriers available for this route.")
        best = couriers[0]
        print(f"Cheapest: {best['courier_name']} @ ₹{best['rate']}")
        return best

    # ── Orders ────────────────────────────────────────────────────────────────

    def create_order(self, order_data: dict) -> dict:
        """
        Create a shipment order.
        Required keys: order_id, order_date, pickup_location,
            billing_* fields, order_items, payment_method, sub_total,
            length, breadth, height, weight
        Returns: {"order_id": ..., "shipment_id": ..., "status": ...}
        """
        res = requests.post(f"{BASE}/orders/create/adhoc",
                            json=order_data, headers=self.headers)
        res.raise_for_status()
        data = res.json()
        print(f"Order created → order_id: {data['order_id']} | shipment_id: {data['shipment_id']}")
        return data

    def get_order(self, order_id: str) -> dict:
        res = requests.get(f"{BASE}/orders/show/{order_id}", headers=self.headers)
        res.raise_for_status()
        return res.json()

    def cancel_orders(self, order_ids: list) -> dict:
        res = requests.post(f"{BASE}/orders/cancel",
                            json={"ids": order_ids}, headers=self.headers)
        res.raise_for_status()
        return res.json()

    # ── AWB / Courier ─────────────────────────────────────────────────────────

    def generate_awb(self, shipment_id: str, courier_id: str) -> str:
        """
        Assign a courier and generate AWB number.
        Returns: AWB code string
        """
        res = requests.post(f"{BASE}/courier/assign/awb", headers=self.headers, json={
            "shipment_id": shipment_id,
            "courier_id":  str(courier_id)
        })
        res.raise_for_status()
        awb = res.json()["response"]["data"]["awb_code"]
        print(f"AWB generated: {awb}")
        return awb

    def request_pickup(self, shipment_ids: list) -> dict:
        """Schedule courier pickup for one or more shipments."""
        res = requests.post(f"{BASE}/courier/generate/pickup",
                            json={"shipment_id": shipment_ids}, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def generate_label(self, shipment_ids: list) -> str:
        """Generate shipping label PDF. Returns download URL."""
        res = requests.post(f"{BASE}/courier/generate/label",
                            json={"shipment_id": shipment_ids}, headers=self.headers)
        res.raise_for_status()
        url = res.json()["label_url"]
        print(f"Label URL: {url}")
        return url

    # ── Tracking ──────────────────────────────────────────────────────────────

    def track_by_awb(self, awb: str) -> dict:
        """Track shipment by AWB code. Returns tracking_data dict."""
        res = requests.get(f"{BASE}/courier/track/awb/{awb}", headers=self.headers)
        res.raise_for_status()
        data = res.json()["tracking_data"]
        try:
            status = data["shipment_track"][0]["current_status"]
            print(f"AWB {awb} → {status}")
        except (KeyError, IndexError):
            pass
        return data

    def track_by_order_id(self, order_id: str) -> dict:
        """Track shipment by Shiprocket order ID."""
        res = requests.get(f"{BASE}/courier/track/order/{order_id}", headers=self.headers)
        res.raise_for_status()
        return res.json()

    def track_multiple_awb(self, awbs: list) -> dict:
        """Batch track up to ~20 AWBs."""
        awb_str = ",".join(awbs)
        res = requests.get(f"{BASE}/courier/track",
                           headers=self.headers, params={"awb": awb_str})
        res.raise_for_status()
        return res.json()

    # ── NDR ───────────────────────────────────────────────────────────────────

    def get_ndr_shipments(self) -> dict:
        """Get all shipments currently in NDR (Non-Delivery Report) state."""
        res = requests.get(f"{BASE}/ndr/all", headers=self.headers)
        res.raise_for_status()
        return res.json()

    def ndr_reattempt(self, awb: str, address1: str, phone: str,
                       address2: str = "", deferred_date: str = "") -> dict:
        """Re-attempt delivery with updated address."""
        params = {
            "awb": awb,
            "address1": address1,
            "address2": address2,
            "phone": phone
        }
        if deferred_date:
            params["deferred_date"] = deferred_date
        res = requests.post(f"{BASE}/ndr/reattempt",
                            headers=self.headers, params=params)
        res.raise_for_status()
        return res.json()

    # ── Quick Full Flow ───────────────────────────────────────────────────────

    def ship_order(self, order_data: dict, pickup_pin: str,
                   delivery_pin: str) -> dict:
        """
        One-shot: Create order → pick cheapest courier → generate AWB → request pickup.
        Returns: {"order_id", "shipment_id", "awb", "courier", "label_url"}
        """
        weight   = order_data.get("weight", 0.5)
        cod      = order_data.get("payment_method", "Prepaid") == "COD"
        courier  = self.cheapest_courier(pickup_pin, delivery_pin, weight, cod)

        order       = self.create_order(order_data)
        shipment_id = str(order["shipment_id"])
        courier_id  = str(courier["courier_company_id"])

        awb       = self.generate_awb(shipment_id, courier_id)
        self.request_pickup([shipment_id])
        label_url = self.generate_label([shipment_id])

        return {
            "order_id":    order["order_id"],
            "shipment_id": shipment_id,
            "awb":         awb,
            "courier":     courier["courier_name"],
            "label_url":   label_url
        }
