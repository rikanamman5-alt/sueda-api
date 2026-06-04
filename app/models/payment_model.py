from database.collections import payments_collection


class PaymentModel:

    @staticmethod
    async def create(payment: dict):
        return await payments_collection.insert_one(payment)

    @staticmethod
    async def get_by_order(order_id: str):
        return await payments_collection.find_one({"order_id": order_id})

    @staticmethod
    async def update_status(order_id: str, status: str):
        return await payments_collection.update_one(
            {"order_id": order_id},
            {"$set": {"status": status}}
        )
