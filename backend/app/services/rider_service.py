import math
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from database.collections import users_collection
from models.delivery_model import DeliveryModel
from models.order_model import OrderModel

BASE_DELIVERY_FEE = 30.0
PER_KM_RATE = 15.0


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RiderService:

    @staticmethod
    async def get_available_riders(seller_id: str | None = None):
        query = {
            "role": "rider",
            "is_available": True,
            "location": {"$ne": None},
        }
        if seller_id:
            query["seller_id"] = seller_id
        cursor = users_collection.find(query)
        return await cursor.to_list(100)

    @staticmethod
    async def find_nearest_rider(lat: float, lng: float, seller_id: str | None = None) -> dict | None:
        riders = await RiderService.get_available_riders(seller_id)
        if not riders:
            return None

        nearest = None
        nearest_dist = float("inf")
        for rider in riders:
            loc = rider.get("location")
            if not loc or "lat" not in loc or "lng" not in loc:
                continue
            dist = haversine(lat, lng, loc["lat"], loc["lng"])
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = rider

        return nearest

    @staticmethod
    def compute_delivery_fee(pickup_lat: float, pickup_lng: float, dropoff_lat: float, dropoff_lng: float) -> tuple[float, float]:
        dist = haversine(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
        fee = BASE_DELIVERY_FEE + (dist * PER_KM_RATE)
        return round(fee, 2), round(dist, 2)

    @staticmethod
    async def auto_assign(order_id: str) -> dict:
        order = await OrderModel.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        seller_id_str = str(order.get("seller_id", ""))
        try:
            seller = await users_collection.find_one({"_id": ObjectId(seller_id_str)})
        except Exception:
            seller = await users_collection.find_one({"_id": seller_id_str})
        if not seller:
            raise ValueError("Seller not found")

        seller_lat = seller.get("shop_lat")
        seller_lng = seller.get("shop_lng")
        buyer_lat = order.get("buyer_lat")
        buyer_lng = order.get("buyer_lng")

        if not all([seller_lat, seller_lng, buyer_lat, buyer_lng]):
            raise ValueError("Missing location data for delivery assignment")

        delivery_fee, total_dist = RiderService.compute_delivery_fee(
            seller_lat, seller_lng, buyer_lat, buyer_lng
        )

        # Priority 1: Same-seller available riders
        rider = await RiderService.find_nearest_rider(seller_lat, seller_lng, seller_id=seller_id_str)

        # Priority 2: Any available rider (different seller)
        if not rider:
            rider = await RiderService.find_nearest_rider(seller_lat, seller_lng)

        if not rider:
            raise ValueError("No available riders found")

        rider_id = str(rider["_id"])

        # Set rider as unavailable
        await users_collection.update_one(
            {"_id": rider["_id"]},
            {"$set": {"is_available": False}},
        )

        # Update order with delivery info
        await OrderModel.update_delivery_info(order_id, {
            "delivery_fee": delivery_fee,
            "delivery_distance_km": total_dist,
            "rider_id": rider_id,
        })

        # Check if delivery record already exists
        existing_delivery = await DeliveryModel.get_by_order(order_id)
        if existing_delivery:
            await DeliveryModel.update(order_id, {
                "rider_id": rider_id,
                "status": "assigned",
                "assigned_at": datetime.utcnow(),
            })
        else:
            delivery = {
                "order_id": order_id,
                "rider_id": rider_id,
            }
            await DeliveryModel.create(delivery)

        return {
            "rider_id": rider_id,
            "rider_name": rider.get("name", ""),
            "rider_contact": rider.get("contact_number", ""),
            "delivery_fee": delivery_fee,
            "delivery_distance_km": total_dist,
        }

    @staticmethod
    async def auto_assign_best(order_id: str) -> dict:
        delivery = await DeliveryModel.get_by_order(order_id)
        if not delivery:
            raise ValueError("Delivery not found")
        if delivery.get("status") != "assigned":
            raise ValueError("Delivery is not in assigned status")

        # Check if 5 min has passed
        assigned_at = delivery.get("assigned_at")
        if assigned_at and datetime.utcnow() - assigned_at < timedelta(minutes=5):
            raise ValueError("Rider still has time to respond")

        # Mark current as expired and free the rider
        old_rider_id = delivery.get("rider_id")
        if old_rider_id:
            try:
                await users_collection.update_one(
                    {"_id": ObjectId(old_rider_id)},
                    {"$set": {"is_available": True}},
                )
            except Exception:
                pass

        return await RiderService.auto_assign(order_id)
