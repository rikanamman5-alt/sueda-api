from fastapi import APIRouter, HTTPException
from bson.objectid import ObjectId
from database.collections import users_collection
from models.product_model import ProductModel
from schemas.order_schema import OrderCreate
from services.order_service import OrderService
from services.notification_service import notify_order_status
from utils.mongo_helpers import fix_mongo

router = APIRouter(tags=["4. Orders"])


async def _enrich_orders(orders: list) -> list:
    result = []
    for o in orders:
        enriched = fix_mongo(o)
        rider_id = o.get("rider_id")
        if rider_id:
            try:
                rider = await users_collection.find_one({"_id": ObjectId(rider_id)})
                if not rider:
                    rider = await users_collection.find_one({"_id": rider_id})
                if rider:
                    enriched["rider"] = {
                        "name": rider.get("name", ""),
                        "contact": rider.get("contact_number", ""),
                    }
            except Exception:
                pass

        items = []
        for item in o.get("items", []):
            product = await ProductModel.get_by_id(item["product_id"])
            items.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "price": item["price"],
                "product_name": product.get("name", "Product") if product else "Product",
                "product_image": product.get("images", [None])[0] if product and product.get("images") else None,
            })
        enriched["items"] = items

        result.append(enriched)
    return result


@router.post("/orders")
async def create_order(order: OrderCreate):
    try:
        result = await OrderService.create_order(order.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
async def get_orders():
    orders = await OrderService.get_all()
    enriched = await _enrich_orders(orders)
    return {"orders": enriched}


@router.get("/orders/buyer/{buyer_id}")
async def get_by_buyer(buyer_id: str):
    orders = await OrderService.get_by_buyer(buyer_id)
    enriched = await _enrich_orders(orders)
    return {"orders": enriched}


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await OrderService.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    enriched = await _enrich_orders([order])
    return enriched[0] if enriched else fix_mongo(order)


@router.delete("/orders/{order_id}")
async def remove_order_from_history(order_id: str):
    order = await OrderService.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("status") != "delivered":
        raise HTTPException(
            status_code=400,
            detail="Only delivered orders can be removed from history",
        )

    await OrderService.remove_from_buyer_history(order_id)
    return {"message": "Order removed from history"}


@router.put("/orders/{order_id}/status")
async def update_status(order_id: str, status: str):
    try:
        await OrderService.update_order_status(order_id, status)
        order = await OrderService.get_by_id(order_id)
        try:
            await notify_order_status(order or {}, status)
        except Exception as e:
            print(f"Push notification skipped: {e}")
        return {"message": f"Order status updated to {status}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    order = await OrderService.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    current_status = order.get("status", "")
    if current_status not in ("pending",):
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be cancelled",
        )
    from models.product_model import ProductModel
    from bson.objectid import ObjectId as OID
    items = order.get("items", [])
    for item in items:
        product = await ProductModel.get_by_id(item["product_id"])
        if product:
            new_stock = (product.get("stock", 0) or 0) + item.get("quantity", 0)
            await ProductModel.update(item["product_id"], {"stock": new_stock})
    await OrderModel.update_status(order_id, "cancelled")
    await OrderModel.update_payment_status(order_id, "refunded")
    order_obj = await OrderService.get_by_id(order_id)
    delivery_id = order_obj.get("delivery_id") if order_obj else None
    if delivery_id:
        try:
            from models.delivery_model import DeliveryModel
            await DeliveryModel.update_status(delivery_id, "cancelled")
        except Exception:
            pass
    try:
        await notify_order_status(order, "cancelled")
    except Exception as e:
        print(f"Push notification skipped: {e}")
    return {"message": "Order cancelled successfully"}
