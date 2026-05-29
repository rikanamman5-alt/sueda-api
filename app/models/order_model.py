from database.collections import orders_collection
from bson.objectid import ObjectId


class OrderModel:

    @staticmethod
    async def create(order: dict):
        return await orders_collection.insert_one(order)

    @staticmethod
    async def get_all():
        return await orders_collection.find().to_list(100)

    @staticmethod
    async def get_by_buyer(buyer_id: str):
        return await orders_collection.find({
            "buyer_id": buyer_id,
            "buyer_removed": {"$ne": True},
        }).to_list(100)

    @staticmethod
    async def get_by_id(order_id: str):
        return await orders_collection.find_one({"_id": ObjectId(order_id)})

    @staticmethod
    async def update_status(order_id: str, status: str):
        return await orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": status}}
        )

    @staticmethod
    async def update_payment_status(order_id: str, payment_status: str):
        return await orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"payment_status": payment_status}}
        )

    @staticmethod
    async def update_delivery_info(order_id: str, data: dict):
        return await orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": data}
        )

    @staticmethod
    async def remove_from_buyer_history(order_id: str):
        return await orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"buyer_removed": True}}
        )

    @staticmethod
    async def delete(order_id: str):
        return await orders_collection.delete_one({"_id": ObjectId(order_id)})
