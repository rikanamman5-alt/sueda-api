from datetime import datetime, timezone
from database.collections import deliveries_collection


class DeliveryModel:

    @staticmethod
    async def create(delivery: dict):
        delivery["status"] = "assigned"
        delivery["assigned_at"] = datetime.now(timezone.utc)
        return await deliveries_collection.insert_one(delivery)

    @staticmethod
    async def get_by_order(order_id: str):
        return await deliveries_collection.find_one({"order_id": order_id})

    @staticmethod
    async def get_by_rider(rider_id: str):
        cursor = deliveries_collection.find({"rider_id": rider_id})
        return await cursor.to_list(100)

    @staticmethod
    async def get_all_assigned():
        cursor = deliveries_collection.find({"status": "assigned"})
        return await cursor.to_list(100)

    @staticmethod
    async def update_status(order_id: str, status: str):
        return await deliveries_collection.update_one(
            {"order_id": order_id},
            {"$set": {"status": status}}
        )

    @staticmethod
    async def update_location(order_id: str, location: dict):
        return await deliveries_collection.update_one(
            {"order_id": order_id},
            {"$set": {"location": location}}
        )

    @staticmethod
    async def update(order_id: str, data: dict):
        return await deliveries_collection.update_one(
            {"order_id": order_id},
            {"$set": data}
        )

    @staticmethod
    async def delete_by_order(order_id: str):
        return await deliveries_collection.delete_one({"order_id": order_id})
