from datetime import datetime
from database.collections import ratings_collection, products_collection, orders_collection
from bson.objectid import ObjectId


class RatingModel:

    @staticmethod
    async def can_user_rate(user_id: str, product_id: str) -> bool:
        order = await orders_collection.find_one({
            "buyer_id": user_id,
            "status": "delivered",
            "items.product_id": product_id,
        })
        return order is not None

    @staticmethod
    async def add_or_update(product_id: str, user_id: str, rating: int):
        existing = await ratings_collection.find_one(
            {"product_id": product_id, "user_id": user_id}
        )
        if existing:
            await ratings_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {"rating": rating, "updated_at": datetime.utcnow()}}
            )
        else:
            await ratings_collection.insert_one({
                "product_id": product_id,
                "user_id": user_id,
                "rating": rating,
                "created_at": datetime.utcnow(),
            })

        await RatingModel._update_product_avg(product_id)

    @staticmethod
    async def get_user_rating(product_id: str, user_id: str):
        rating = await ratings_collection.find_one(
            {"product_id": product_id, "user_id": user_id}
        )
        return rating

    @staticmethod
    async def get_product_ratings(product_id: str):
        pipeline = [
            {"$match": {"product_id": product_id}},
            {
                "$group": {
                    "_id": None,
                    "avgRating": {"$avg": "$rating"},
                    "numRatings": {"$sum": 1},
                }
            },
        ]
        result = await ratings_collection.aggregate(pipeline).to_list(1)
        if result:
            return round(result[0]["avgRating"], 1), result[0]["numRatings"]
        return 0.0, 0

    @staticmethod
    async def get_user_reviews(user_id: str, page: int = 1, limit: int = 20):
        skip = (page - 1) * limit
        cursor = ratings_collection.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
        ratings = await cursor.to_list(length=limit)
        total = await ratings_collection.count_documents({"user_id": user_id})
        result = []
        for r in ratings:
            product = await products_collection.find_one({"_id": ObjectId(r["product_id"])})
            if not product:
                product = await products_collection.find_one({"_id": r["product_id"]})
            result.append({
                "product_id": r["product_id"],
                "product_name": product.get("name", "Product") if product else "Product",
                "product_image": product.get("images", [None])[0] if product and product.get("images") else None,
                "rating": r["rating"],
                "created_at": r.get("created_at"),
            })
        return {"reviews": result, "total": total, "page": page, "limit": limit}

    @staticmethod
    async def get_rateable_products(user_id: str):
        pipeline = [
            {"$match": {"buyer_id": user_id, "status": "delivered"}},
            {"$unwind": "$items"},
            {"$group": {"_id": "$items.product_id"}},
        ]
        product_ids = await orders_collection.aggregate(pipeline).to_list(100)
        ids = [p["_id"] for p in product_ids if p.get("_id")]
        if not ids:
            return []

        already_rated = ratings_collection.find({"user_id": user_id})
        rated_ids = set()
        async for r in already_rated:
            rated_ids.add(r["product_id"])

        unrated = [pid for pid in ids if pid not in rated_ids]
        result = []
        for pid in unrated:
            product = await products_collection.find_one({"_id": ObjectId(pid)})
            if not product:
                product = await products_collection.find_one({"_id": pid})
            if product:
                result.append({
                    "product_id": pid,
                    "name": product.get("name", "Product"),
                    "images": product.get("images", []),
                    "price": product.get("price", 0),
                })
        return result

    @staticmethod
    async def _update_product_avg(product_id: str):
        avg, count = await RatingModel.get_product_ratings(product_id)
        update_result = await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"avgRating": avg, "numRatings": count}}
        )
        if update_result.matched_count == 0:
            await products_collection.update_one(
                {"_id": product_id},
                {"$set": {"avgRating": avg, "numRatings": count}}
            )
