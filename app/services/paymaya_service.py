import hashlib
import hmac
import json

import requests
from core.config import PAYMAYA_SECRET

BASE_URL = "https://pg-sandbox.paymaya.com/checkout/v1"


class PayMayaService:

    @staticmethod
    def create_checkout(order_id: str, amount: float, items: list[dict] = None, redirect_base: str = None):
        if redirect_base is None:
            redirect_base = "http://localhost:8000"

        if not items:
            items = [{"name": f"Order {order_id}", "quantity": 1, "amount": amount}]

        payload_items = []
        for item in items:
            payload_items.append({
                "name": item.get("name", "Item"),
                "quantity": item.get("quantity", 1),
                "totalAmount": {
                    "value": float(item.get("amount", 0)),
                    "currency": "PHP"
                }
            })

        payload = {
            "totalAmount": {
                "value": amount,
                "currency": "PHP"
            },
            "items": payload_items,
            "redirectUrl": {
                "success": f"{redirect_base}/pay/success?order_id={order_id}",
                "failure": f"{redirect_base}/pay/fail?order_id={order_id}",
                "cancel": f"{redirect_base}/pay/cancel?order_id={order_id}"
            }
        }

        response = requests.post(
            f"{BASE_URL}/checkout",
            json=payload,
            auth=(PAYMAYA_SECRET, "")
        )

        return response.json()

    @staticmethod
    def verify_signature(body: bytes, signature_header: str) -> bool:
        if not signature_header:
            return False
        expected = hmac.new(
            PAYMAYA_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)
