from models.payment_model import PaymentModel
from models.order_model import OrderModel

PAYMENT_FLOW = {
    "pending": {"paid", "failed"},
    "paid": set(),
    "failed": {"paid"},
}


class PaymentService:

    @staticmethod
    async def create_payment_record(order_id: str, amount: float, checkout_id: str = None):
        payment_data = {
            "order_id": order_id,
            "amount": amount,
            "status": "pending",
            "checkout_id": checkout_id,
        }
        return await PaymentModel.create(payment_data)

    @staticmethod
    async def handle_webhook(payload: dict):
        order_id = payload.get("order_id")
        status = payload.get("status")

        if status == "paid":
            return await PaymentService.process_success(order_id)
        elif status == "failed":
            return await PaymentService.process_failure(order_id)

        raise ValueError(f"Unknown webhook status: {status}")

    @staticmethod
    async def process_success(order_id: str):
        payment = await PaymentModel.get_by_order(order_id)
        if payment:
            current = payment["status"]
            allowed = PAYMENT_FLOW.get(current, set())
            if "paid" not in allowed:
                raise ValueError(f"Cannot mark payment as paid from '{current}'")

        await PaymentModel.update_status(order_id, "paid")
        await OrderModel.update_status(order_id, "paid")
        await OrderModel.update_payment_status(order_id, "paid")

        try:
            from services.rider_service import RiderService
            await RiderService.auto_assign(order_id)
        except ValueError as e:
            pass

        return {"message": "Payment successful", "order_id": order_id}

    @staticmethod
    async def process_failure(order_id: str):
        await PaymentModel.update_status(order_id, "failed")
        return {"message": "Payment failed", "order_id": order_id}
