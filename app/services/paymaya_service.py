import hashlib
import hmac
import json

import requests
from core.config import PAYMAYA_SECRET

BASE_URL = "https://pg-sandbox.paymaya.com/checkout/v1"


class PayMayaService:

    @staticmethod
    def create_checkout(order_id: str, amount: float):
        payload = {
            "totalAmount": {
                "value": amount,
                "currency": "PHP"
            },
            "items": [
                {
                    "name": f"Order {order_id}",
                    "quantity": 1,
                    "totalAmount": {
                        "value": amount,
                        "currency": "PHP"
                    }
                }
            ],
            "redirectUrl": {
                "success": f"http://localhost:8000/pay/success?order_id={order_id}",
                "failure": "http://localhost:8000/pay/fail",
                "cancel": "http://localhost:8000/pay/cancel"
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
