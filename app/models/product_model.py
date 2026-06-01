from database.collections import products_collection
from bson.objectid import ObjectId
from utils.mongo_helpers import fix_mongo


class ProductModel:

    @staticmethod
    async def create(product: dict):
        return await products_collection.insert_one(product)

    @staticmethod
    async def get_all():
        return await products_collection.find().to_list(100)

    @staticmethod
    async def get_all_count():
        return await products_collection.count_documents({})

    @staticmethod
    async def get_by_id(product_id: str):
        result = await products_collection.find_one({"_id": ObjectId(product_id)})
        if result is None:
            result = await products_collection.find_one({"_id": product_id})
        return fix_mongo(result)

    @staticmethod
    async def get_by_seller(seller_id: str):
        products = await products_collection.find({"seller_id": seller_id}).to_list(100)
        return fix_mongo(products)

    @staticmethod
    async def search(
        search: str = None,
        category: str = None,
        min_price: float = None,
        max_price: float = None,
        sort_by: str = "created_at",
        sort_order: int = -1,
        page: int = 1,
        limit: int = 20,
    ):
        query = {}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]
        if category:
            query["category"] = category
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            query["price"] = price_filter

        skip = (page - 1) * limit
        sort_field = sort_by if sort_by in ("price", "name", "created_at") else "created_at"
        total = await products_collection.count_documents(query)
        cursor = (
            products_collection.find(query)
            .sort(sort_field, sort_order)
            .skip(skip)
            .limit(limit)
        )
        products = await cursor.to_list(length=limit)
        return {
            "products": fix_mongo(products),
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    @staticmethod
    async def update(product_id: str, data: dict):
        result = await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": data}
        )
        if result.matched_count == 0:
            result = await products_collection.update_one(
                {"_id": product_id},
                {"$set": data}
            )
        return result

    @staticmethod
    async def delete(product_id: str):
        result = await products_collection.delete_one({"_id": ObjectId(product_id)})
        if result.deleted_count == 0:
            result = await products_collection.delete_one({"_id": product_id})
        return result
