from database.mongo import db

users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]
payments_collection = db["payments"]
deliveries_collection = db["deliveries"]
refresh_tokens_collection = db["refresh_tokens"]
carts_collection = db["carts"]
ratings_collection = db["ratings"]
