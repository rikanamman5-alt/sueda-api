from database.collections import carts_collection
from bson.objectid import ObjectId


class CartModel:

    @staticmethod
    async def get_by_user(user_id: str):
        return await carts_collection.find_one({"user_id": user_id})

    @staticmethod
    async def upsert(user_id: str, items: list):
        return await carts_collection.update_one(
            {"user_id": user_id},
            {"$set": {"items": items}},
            upsert=True,
        )

    @staticmethod
    async def add_item(user_id: str, item: dict):
        cart = await carts_collection.find_one({"user_id": user_id})
        if not cart:
            return await carts_collection.insert_one(
                {"user_id": user_id, "items": [item]}
            )

        existing = None
        for i in cart["items"]:
            if i["product_id"] == item["product_id"]:
                existing = i
                break

        if existing:
            return await carts_collection.update_one(
                {"user_id": user_id, "items.product_id": item["product_id"]},
                {"$inc": {"items.$.quantity": item["quantity"]}},
            )
        else:
            return await carts_collection.update_one(
                {"user_id": user_id},
                {"$push": {"items": item}},
            )

    @staticmethod
    async def remove_item(user_id: str, product_id: str):
        return await carts_collection.update_one(
            {"user_id": user_id},
            {"$pull": {"items": {"product_id": product_id}}},
        )

    @staticmethod
    async def update_item_quantity(user_id: str, product_id: str, quantity: int):
        return await carts_collection.update_one(
            {"user_id": user_id, "items.product_id": product_id},
            {"$set": {"items.$.quantity": quantity}},
        )

    @staticmethod
    async def clear(user_id: str):
        return await carts_collection.update_one(
            {"user_id": user_id},
            {"$set": {"items": []}},
        )

    @staticmethod
    async def delete_cart(user_id: str):
        return await carts_collection.delete_one({"user_id": user_id})
