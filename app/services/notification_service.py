from datetime import datetime
from bson.objectid import ObjectId
from database.collections import users_collection
from services.websocket_manager import ws_manager

STATUS_LABELS = {
    "pending": "Order Placed",
    "paid": "Payment Confirmed",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "refunded": "Refunded",
}


async def create_notification(email: str, title: str, message: str, data: dict | None = None):
    notification = {
        "id": str(ObjectId()),
        "title": title,
        "message": message,
        "time": datetime.utcnow().isoformat(),
        "read": False,
        "data": data or {},
    }

    await users_collection.update_one(
        {"email": email},
        {"$push": {"notifications": {"$each": [notification], "$position": 0}}},
    )

    await ws_manager.notify_user(email, {
        "type": "notification",
        "notification": notification,
    })


async def notify_order_status(order: dict, new_status: str):
    buyer_email = order.get("buyer_email") or order.get("buyer_id")
    seller_id = order.get("seller_id")
    order_id_str = str(order.get("_id", ""))
    short_id = order_id_str[-8:]
    label = STATUS_LABELS.get(new_status, new_status.capitalize())

    if buyer_email:
        await create_notification(
            buyer_email,
            f"Order #{short_id} {label}",
            f"Your order has been updated to: {label}",
            {"type": "order_status", "order_id": order_id_str, "status": new_status},
        )

    if seller_id and new_status in ("paid", "cancelled", "refunded"):
        seller_email = None
        try:
            seller = await users_collection.find_one({"_id": ObjectId(seller_id)})
            if seller:
                seller_email = seller.get("email")
        except Exception:
            pass
        if seller_email:
            await create_notification(
                seller_email,
                f"Order #{short_id} {label}",
                f"A buyer's order has been updated to: {label}",
                {"type": "order_status", "order_id": order_id_str, "status": new_status},
            )
