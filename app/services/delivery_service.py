from datetime import datetime, timedelta
from bson.objectid import ObjectId
from database.collections import users_collection
from models.delivery_model import DeliveryModel
from models.order_model import OrderModel
from fastapi import HTTPException
from services.websocket_manager import ws_manager
from utils.mongo_helpers import fix_mongo

DELIVERY_FLOW = {
    "assigned": {"accepted", "expired", "cancelled"},
    "accepted": {"picked_up"},
    "picked_up": {"in_transit"},
    "in_transit": {"delivered"},
    "delivered": set(),
    "expired": set(),
    "cancelled": set(),
}


class DeliveryService:

    @staticmethod
    async def assign_rider(order_id: str, rider_id: str):
        order = await OrderModel.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
        rider = await users_collection.find_one(
            {"_id": ObjectId(rider_id), "role": "rider"},
            {"password_hash": 0, "refresh_token": 0},
        )
        if not rider:
            raise ValueError("Rider not found")

        # Allow COD orders to be assigned even if unpaid
        payment_method = order.get("payment_method", "")
        payment_status = order.get("payment_status", "unpaid")

        if payment_method.lower() not in ("cod", "cash on delivery") and payment_status != "paid":
            raise HTTPException(
                status_code=400,
                detail="Order must be paid before assigning a rider"
            )

        existing_delivery = await DeliveryModel.get_by_order(order_id)
        if existing_delivery:
            current_status = existing_delivery.get("status")
            if current_status in ("accepted", "picked_up", "in_transit", "delivered"):
                raise ValueError(
                    f"Order already has a delivery with status '{current_status}'"
                )

            old_rider_id = existing_delivery.get("rider_id")
            if old_rider_id and old_rider_id != rider_id:
                try:
                    await users_collection.update_one(
                        {"_id": ObjectId(old_rider_id)},
                        {
                            "$set": {
                                "is_available": True,
                                "rider_status": "available",
                                "current_order_id": None,
                            }
                        },
                    )
                except Exception:
                    pass

            await DeliveryModel.update(
                order_id,
                {
                    "rider_id": rider_id,
                    "status": "assigned",
                    "assigned_at": datetime.utcnow(),
                },
            )
            result = None
        else:
            delivery = {
                "order_id": order_id,
                "rider_id": rider_id,
            }
            result = await DeliveryModel.create(delivery)

        await OrderModel.update_delivery_info(
            order_id,
            {"rider_id": rider_id, "delivery_status": "assigned"},
        )

        try:
            await users_collection.update_one(
                {"_id": ObjectId(rider_id)},
                {
                    "$set": {
                        "is_available": False,
                        "rider_status": "assigned",
                        "current_order_id": order_id,
                    }
                },
            )
        except Exception:
            pass

        rider_name = rider.get("name", "Rider") if rider else "Rider"

        await ws_manager.broadcast_rider_status_change(
            rider_id=rider_id,
            status="assigned",
            name=rider_name,
        )

        enriched = {
            "order": fix_mongo(order),
            "assigned_rider": fix_mongo(rider) if rider else None,
        }
        await ws_manager.broadcast_new_delivery(
            order_id=order_id,
            rider_id=rider_id,
            delivery_data=enriched,
        )

        return result

    @staticmethod
    async def accept_assignment(order_id: str, rider_id: str):
        delivery = await DeliveryModel.get_by_order(order_id)
        if not delivery:
            raise ValueError("Delivery not found")
        if delivery.get("status") != "assigned":
            raise ValueError("Delivery is not in assigned status")
        if delivery.get("rider_id") != rider_id:
            raise ValueError("This delivery is not assigned to you")

        await DeliveryModel.update_status(order_id, "accepted")
        try:
            await users_collection.update_one(
                {"_id": ObjectId(rider_id)},
                {"$set": {"rider_status": "delivering"}},
            )
        except Exception:
            pass

        await ws_manager.broadcast_rider_status_change(
            rider_id=rider_id,
            status="delivering",
            name="",
        )
        await ws_manager.broadcast_delivery_status_change(
            order_id=order_id,
            status="accepted",
            rider_id=rider_id,
        )

        return {"message": "Delivery accepted"}

    @staticmethod
    async def cancel_assignment(order_id: str):
        delivery = await DeliveryModel.get_by_order(order_id)
        if not delivery:
            raise ValueError("Delivery not found")
        if delivery.get("status") not in ("assigned", "expired"):
            raise ValueError("Can only cancel assigned or expired deliveries")

        rider_id = delivery.get("rider_id")
        if rider_id:
            try:
                await users_collection.update_one(
                    {"_id": ObjectId(rider_id)},
                    {
                        "$set": {
                            "is_available": True,
                            "rider_status": "available",
                            "current_order_id": None,
                        }
                    },
                )
                rider = await users_collection.find_one({"_id": ObjectId(rider_id)})
                rider_name = rider.get("name", "Rider") if rider else "Rider"
                await ws_manager.broadcast_rider_status_change(
                    rider_id=rider_id,
                    status="available",
                    name=rider_name,
                )
            except Exception:
                pass

        await DeliveryModel.update(order_id, {"status": "cancelled", "rider_id": None})
        await OrderModel.update_delivery_info(order_id, {"rider_id": None})
        return {"message": "Assignment cancelled"}

    @staticmethod
    async def reassign_rider(order_id: str):
        delivery = await DeliveryModel.get_by_order(order_id)
        if not delivery:
            raise ValueError("Delivery not found")

        old_rider_id = delivery.get("rider_id")
        old_status = delivery.get("status")

        free_old = old_status in ("assigned", "expired")
        if free_old and old_rider_id:
            try:
                await users_collection.update_one(
                    {"_id": ObjectId(old_rider_id)},
                    {
                        "$set": {
                            "is_available": True,
                            "rider_status": "available",
                            "current_order_id": None,
                        }
                    },
                )
                rider = await users_collection.find_one({"_id": ObjectId(old_rider_id)})
                rider_name = rider.get("name", "Rider") if rider else "Rider"
                await ws_manager.broadcast_rider_status_change(
                    rider_id=old_rider_id,
                    status="available",
                    name=rider_name,
                )
            except Exception:
                pass

        from services.rider_service import RiderService
        result = await RiderService.auto_assign(order_id)

        await DeliveryModel.update(order_id, {
            "status": "assigned",
            "rider_id": result["rider_id"],
            "assigned_at": datetime.utcnow(),
        })

        return result

    @staticmethod
    async def check_timeouts():
        assigned = await DeliveryModel.get_all_assigned()
        now = datetime.utcnow()
        expired = []
        for d in assigned:
            assigned_at = d.get("assigned_at")
            if assigned_at and now - assigned_at > timedelta(minutes=5):
                expired.append(d["order_id"])
        return expired

    @staticmethod
    async def process_expired(order_id: str):
        delivery = await DeliveryModel.get_by_order(order_id)
        if not delivery:
            raise ValueError("Delivery not found")
        if delivery.get("status") != "assigned":
            return {"message": "Already processed"}

        await DeliveryModel.update(order_id, {"status": "expired", "rider_id": None})
        rider_id = delivery.get("rider_id")
        if rider_id:
            try:
                await users_collection.update_one(
                    {"_id": ObjectId(rider_id)},
                    {
                        "$set": {
                            "is_available": True,
                            "rider_status": "available",
                            "current_order_id": None,
                        }
                    },
                )
            except Exception:
                pass

        return await DeliveryService.reassign_rider(order_id)

    @staticmethod
    async def update_status(order_id: str, new_status: str):
        delivery = await DeliveryModel.get_by_order(order_id)
        if not delivery:
            raise ValueError("Delivery not found")

        current = delivery["status"]
        allowed = DELIVERY_FLOW.get(current, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition delivery from '{current}' to '{new_status}'"
            )

        await DeliveryModel.update_status(order_id, new_status)
        await OrderModel.update_delivery_info(order_id, {"delivery_status": new_status})

        rider_id = delivery.get("rider_id")

        if new_status == "delivered":
            await OrderModel.update_status(order_id, "delivered")
            if rider_id:
                try:
                    await users_collection.update_one(
                        {"_id": ObjectId(rider_id)},
                        {
                            "$set": {
                                "is_available": True,
                                "rider_status": "available",
                                "current_order_id": None,
                            }
                        },
                    )
                    rider = await users_collection.find_one({"_id": ObjectId(rider_id)})
                    rider_name = rider.get("name", "Rider") if rider else "Rider"
                    await ws_manager.broadcast_rider_status_change(
                        rider_id=rider_id,
                        status="available",
                        name=rider_name,
                    )
                except Exception:
                    pass

        if rider_id:
            await ws_manager.broadcast_delivery_status_change(
                order_id=order_id,
                status=new_status,
                rider_id=rider_id,
            )

    @staticmethod
    async def update_location(order_id: str, location: dict):
        return await DeliveryModel.update_location(order_id, location)

    @staticmethod
    async def get_by_order(order_id: str):
        return await DeliveryModel.get_by_order(order_id)
