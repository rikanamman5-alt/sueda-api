from datetime import datetime, timezone
from models.order_model import OrderModel
from models.product_model import ProductModel
from services.paymaya_service import PayMayaService
from models.payment_model import PaymentModel
from services.rider_service import RiderService

ORDER_FLOW = {
    "pending": {"paid"},
    "paid": {"shipped"},
    "shipped": {"delivered"},
    "delivered": set(),
}


class OrderService:

    @staticmethod
    async def create_order(order_data: dict):
        subtotal = sum(item["price"] * item["quantity"] for item in order_data["items"])

        delivery_fee = order_data.get("delivery_fee") or 0.0
        seller_lat = None
        seller_lng = None

        seller_id_str = str(order_data.get("seller_id", ""))
        try:
            from bson.objectid import ObjectId
            from database.collections import users_collection
            seller = await users_collection.find_one({"_id": ObjectId(seller_id_str)})
            if seller:
                seller_lat = seller.get("shop_lat")
                seller_lng = seller.get("shop_lng")
        except Exception:
            pass

        buyer_lat = order_data.get("buyer_lat")
        buyer_lng = order_data.get("buyer_lng")

        if all([seller_lat, seller_lng, buyer_lat, buyer_lng]):
            delivery_fee, delivery_dist = RiderService.compute_delivery_fee(
                seller_lat, seller_lng, buyer_lat, buyer_lng
            )
            order_data["delivery_distance_km"] = delivery_dist

        total = round(subtotal + delivery_fee, 2)
        order_data["subtotal"] = subtotal
        order_data["delivery_fee"] = delivery_fee
        order_data["total_price"] = total
        order_data["status"] = "pending"
        order_data["payment_status"] = "unpaid"

        order_data["created_at"] = datetime.now(timezone.utc)
        result = await OrderModel.create(order_data)
        order_id = str(result.inserted_id)

        checkout_url = None
        try:
            checkout = await PayMayaService.create_checkout(order_id, total)
            checkout_url = checkout.get("redirectUrl")
            payment_data = {
                "order_id": order_id,
                "amount": total,
                "status": "pending",
                "checkout_id": checkout.get("checkoutId"),
            }
            await PaymentModel.create(payment_data)
        except Exception as e:
            print(f"PayMaya checkout skipped: {e}")

        # Auto-assign a rider after order creation
        rider_assignment = None
        try:
            rider_assignment = await RiderService.auto_assign(order_id)
        except Exception as e:
            print(f"Auto-assign skipped: {e}")

        order_data["_id"] = order_id
        order_data["checkout_url"] = checkout_url
        order_data["rider_assignment"] = rider_assignment
        return order_data

    @staticmethod
    async def update_order_status(order_id: str, new_status: str):
        order = await OrderModel.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        current = order["status"]
        allowed = ORDER_FLOW.get(current, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{current}' to '{new_status}'"
            )

        await OrderModel.update_status(order_id, new_status)

    @staticmethod
    async def get_all():
        return await OrderModel.get_all()

    @staticmethod
    async def get_by_buyer(buyer_id: str):
        return await OrderModel.get_by_buyer(buyer_id)

    @staticmethod
    async def get_by_id(order_id: str):
        return await OrderModel.get_by_id(order_id)

    @staticmethod
    async def remove_from_buyer_history(order_id: str):
        return await OrderModel.remove_from_buyer_history(order_id)
