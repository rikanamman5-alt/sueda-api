from models.cart_model import CartModel
from models.product_model import ProductModel


class CartService:

    @staticmethod
    async def add_item(user_id: str, product_id: str, quantity: int):
        product = await ProductModel.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found")

        if product["stock"] < quantity:
            raise ValueError(f"Insufficient stock. Available: {product['stock']}")

        item = {"product_id": product_id, "quantity": quantity}
        await CartModel.add_item(user_id, item)
        return await CartService.get_cart(user_id)

    @staticmethod
    async def remove_item(user_id: str, product_id: str):
        await CartModel.remove_item(user_id, product_id)
        return await CartService.get_cart(user_id)

    @staticmethod
    async def update_item_quantity(user_id: str, product_id: str, quantity: int):
        if quantity < 1:
            return await CartService.remove_item(user_id, product_id)

        product = await ProductModel.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found")

        if product["stock"] < quantity:
            raise ValueError(f"Insufficient stock. Available: {product['stock']}")

        await CartModel.update_item_quantity(user_id, product_id, quantity)
        return await CartService.get_cart(user_id)

    @staticmethod
    async def get_cart(user_id: str):
        cart = await CartModel.get_by_user(user_id)
        if not cart or not cart.get("items"):
            return {"user_id": user_id, "items": [], "total_price": 0.0}

        items_with_details = []
        total = 0.0
        for item in cart["items"]:
            product = await ProductModel.get_by_id(item["product_id"])
            if product:
                item_total = product["price"] * item["quantity"]
                total += item_total
                items_with_details.append({
                    "product_id": item["product_id"],
                    "name": product["name"],
                    "price": product["price"],
                    "image": product["images"][0] if product.get("images") else None,
                    "stock": product["stock"],
                    "quantity": item["quantity"],
                    "item_total": item_total,
                    "seller_id": str(product.get("seller_id", "")),
                })

        return {
            "user_id": user_id,
            "items": items_with_details,
            "total_price": round(total, 2),
        }

    @staticmethod
    async def clear_cart(user_id: str):
        await CartModel.clear(user_id)
        return {"message": "Cart cleared"}
