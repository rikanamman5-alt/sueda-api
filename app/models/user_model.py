from datetime import datetime, timezone
from database.collections import users_collection


class UserModel:

    @staticmethod
    async def create_user(user_data: dict):
        user_data["role"] = user_data.get("role", "buyer")
        return await users_collection.insert_one(user_data)

    @staticmethod
    async def get_user(email: str):
        return await users_collection.find_one({"email": email})

    @staticmethod
    async def update_user(email: str, data: dict):
        return await users_collection.update_one(
            {"email": email},
            {"$set": data}
        )

    @staticmethod
    async def delete_user(email: str):
        return await users_collection.delete_one({"email": email})

    @staticmethod
    async def update_last_login(email: str):
        return await users_collection.update_one(
            {"email": email},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )

    @staticmethod
    async def add_to_wishlist(email: str, product_id: str):
        return await users_collection.update_one(
            {"email": email},
            {"$addToSet": {"wishlist": product_id}}
        )

    @staticmethod
    async def remove_from_wishlist(email: str, product_id: str):
        return await users_collection.update_one(
            {"email": email},
            {"$pull": {"wishlist": product_id}}
        )
