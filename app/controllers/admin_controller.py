from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from utils.deps import require_role
from database.collections import users_collection, products_collection, orders_collection, payments_collection, deliveries_collection
from bson.objectid import ObjectId
from models.product_model import ProductModel
from models.order_model import OrderModel

router = APIRouter(tags=["Admin"], prefix="/admin")


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    status: str


class ProductUpdateData(BaseModel):
    name: str | None = None
    price: float | None = None
    category: str | None = None
    stock: int | None = None
    description: str | None = None
    images: list | None = None


@router.get("/dashboard")
async def admin_dashboard(admin=Depends(require_role(["admin"]))):
    total_users = await users_collection.count_documents({})
    total_buyers = await users_collection.count_documents({"role": "buyer"})
    total_sellers = await users_collection.count_documents({"role": "seller"})
    total_riders = await users_collection.count_documents({"role": "rider"})
    total_products = await products_collection.count_documents({})
    total_orders = await orders_collection.count_documents({})
    available_riders = await users_collection.count_documents({"role": "rider", "is_available": True})

    revenue_pipeline = [
        {"$match": {"status": "delivered"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
    ]
    revenue_result = await orders_collection.aggregate(revenue_pipeline).to_list(1)
    total_revenue = revenue_result[0]["total"] if revenue_result else 0

    recent_orders = await orders_collection.find().sort("created_at", -1).limit(10).to_list(10)
    orders_list = []
    for o in recent_orders:
        buyer = await users_collection.find_one({"_id": ObjectId(o["buyer_id"])}) if o.get("buyer_id") else None
        orders_list.append({
            "id": str(o["_id"]),
            "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
            "status": o.get("status", ""),
            "total": o.get("total", 0),
            "created_at": str(o.get("created_at", "")),
        })

    riders = await users_collection.find(
        {"role": "rider"},
        {"name": 1, "email": 1, "picture": 1, "is_available": 1, "contact_number": 1, "location": 1}
    ).sort("name", 1).to_list(100)
    riders_list = []
    for r in riders:
        riders_list.append({
            "id": str(r["_id"]),
            "name": r.get("name", ""),
            "email": r.get("email", ""),
            "picture": r.get("picture", ""),
            "is_available": r.get("is_available", False),
            "contact_number": r.get("contact_number", ""),
            "location": r.get("location"),
        })

    return {
        "stats": {
            "total_users": total_users,
            "total_buyers": total_buyers,
            "total_sellers": total_sellers,
            "total_riders": total_riders,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "available_riders": available_riders,
        },
        "recent_orders": orders_list,
        "riders": riders_list,
    }


@router.get("/users")
async def admin_list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    role: str = Query(None),
    admin=Depends(require_role(["admin"])),
):
    query = {}
    if role:
        query["role"] = role
    skip = (page - 1) * limit
    total = await users_collection.count_documents(query)
    users = await users_collection.find(query).sort("_id", -1).skip(skip).to_list(length=limit)
    result = []
    for u in users:
        result.append({
            "id": str(u["_id"]),
            "email": u.get("email", ""),
            "name": u.get("name", ""),
            "role": u.get("role", "buyer"),
            "banned": u.get("banned", False),
            "provider": u.get("provider", "email"),
            "contact_number": u.get("contact_number", ""),
            "address": u.get("address", ""),
            "picture": u.get("picture") or u.get("avatar") or "",
            "verification_status": u.get("verification_status", ""),
            "verification_reject_reason": u.get("verification_reject_reason", ""),
            "license_number": u.get("license_number", ""),
        })
    return {"users": result, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}


@router.get("/users/{user_id}")
async def admin_get_user_detail(
    user_id: str,
    admin=Depends(require_role(["admin"])),
):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = {
        "id": str(user["_id"]),
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "role": user.get("role", "buyer"),
        "banned": user.get("banned", False),
        "provider": user.get("provider", "email"),
        "contact_number": user.get("contact_number", ""),
        "address": user.get("address", ""),
        "picture": user.get("picture", ""),
        "created_at": str(user.get("created_at", "")),
    }

    role = user.get("role", "")

    # Seller-specific details
    if role == "seller":
        result["shop_name"] = user.get("shop_name", "")
        result["shop_description"] = user.get("shop_description", "")
        result["shop_lat"] = user.get("shop_lat")
        result["shop_lng"] = user.get("shop_lng")
        result["shop_logo"] = user.get("shop_logo", "")
        result["shop_banner"] = user.get("shop_banner", "")
        result["contact_email"] = user.get("contact_email", "")
        result["contact_phone"] = user.get("contact_phone", "")
        result["business_permit"] = user.get("business_permit", "")
        result["operating_hours"] = user.get("operating_hours", "")
        result["verification_status"] = user.get("verification_status", "")
        result["verification_reject_reason"] = user.get("verification_reject_reason", "")

        product_count = await products_collection.count_documents({"seller_id": user_id})
        seller_orders = await orders_collection.find({"seller_id": user_id}).to_list(200)
        total_orders = len(seller_orders)
        total_revenue = sum(o.get("total_price", 0) or 0 for o in seller_orders if o.get("status") == "delivered")
        result["product_count"] = product_count
        result["total_orders"] = total_orders
        result["total_revenue"] = total_revenue

    # Buyer-specific details
    elif role == "buyer":
        buyer_orders = await orders_collection.find({"buyer_id": user_id}).to_list(200)
        total_orders = len(buyer_orders)
        total_spent = sum(o.get("total_price", 0) or 0 for o in buyer_orders)
        result["total_orders"] = total_orders
        result["total_spent"] = total_spent

    # Rider-specific details
    elif role == "rider":
        result["license_number"] = user.get("license_number", "")
        result["vehicle_brand"] = user.get("vehicle_brand", "")
        result["vehicle_model"] = user.get("vehicle_model", "")
        result["vehicle_plate"] = user.get("vehicle_plate", "")
        result["vehicle_color"] = user.get("vehicle_color", "")
        result["is_available"] = user.get("is_available", False)
        result["rider_status"] = user.get("rider_status", "")
        result["current_order_id"] = user.get("current_order_id", "")
        result["location"] = user.get("location")
        result["verification_status"] = user.get("verification_status", "")
        result["verification_reject_reason"] = user.get("verification_reject_reason", "")
        result["verification_doc"] = user.get("verification_doc", "")

        rider_deliveries = await deliveries_collection.find({"rider_id": user_id}).to_list(200)
        total_deliveries = len(rider_deliveries)
        completed_count = sum(1 for d in rider_deliveries if d.get("status") == "delivered")
        # Earnings from completed order delivery_fees
        total_earnings = 0.0
        for d in rider_deliveries:
            if d.get("status") == "delivered":
                order = await orders_collection.find_one({"_id": ObjectId(d["order_id"])})
                if order:
                    total_earnings += order.get("delivery_fee", 0) or 0
        result["total_deliveries"] = total_deliveries
        result["completed_deliveries"] = completed_count
        result["total_earnings"] = round(total_earnings, 2)

    return {"user": result}


@router.get("/verifications")
async def admin_list_verifications(
    status: str = "pending",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_role(["admin"])),
):
    query = {"verification_status": status, "role": {"$in": ["rider", "seller"]}}
    skip = (page - 1) * limit
    total = await users_collection.count_documents(query)
    users = await users_collection.find(query).sort("_id", -1).skip(skip).to_list(length=limit)
    result = []
    for u in users:
        result.append({
            "id": str(u["_id"]),
            "email": u.get("email", ""),
            "name": u.get("name", ""),
            "role": u.get("role", ""),
            "verification_status": u.get("verification_status", ""),
            "verification_reject_reason": u.get("verification_reject_reason", ""),
            "verification_doc": u.get("verification_doc", ""),
            "vehicle_brand": u.get("vehicle_brand", ""),
            "vehicle_model": u.get("vehicle_model", ""),
            "vehicle_plate": u.get("vehicle_plate", ""),
            "vehicle_color": u.get("vehicle_color", ""),
            "business_permit": u.get("business_permit", ""),
            "operating_hours": u.get("operating_hours", ""),
            "license_number": u.get("license_number", ""),
            "contact_number": u.get("contact_number", ""),
        })
    return {"verifications": result, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}


@router.patch("/verifications/{user_id}/approve")
async def admin_approve_verification(
    user_id: str,
    admin=Depends(require_role(["admin"])),
):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("verification_status") != "pending":
        raise HTTPException(status_code=400, detail="User has no pending verification")
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"verification_status": "verified", "verification_reject_reason": ""}},
    )
    return {"verification_status": "verified", "message": "User verified successfully"}


@router.patch("/verifications/{user_id}/reject")
async def admin_reject_verification(
    user_id: str,
    data: dict,
    admin=Depends(require_role(["admin"])),
):
    reason = data.get("reason", "")
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("verification_status") != "pending":
        raise HTTPException(status_code=400, detail="User has no pending verification")
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"verification_status": "rejected", "verification_reject_reason": reason}},
    )
    return {"verification_status": "rejected", "message": "User verification rejected"}


@router.patch("/users/{user_id}/ban")
async def admin_toggle_ban(user_id: str, admin=Depends(require_role(["admin"]))):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_status = not user.get("banned", False)
    await users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"banned": new_status}})
    return {"banned": new_status}


@router.patch("/users/{user_id}/role")
async def admin_change_role(user_id: str, data: RoleUpdate, admin=Depends(require_role(["admin"]))):
    if data.role not in ("buyer", "seller", "rider", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": data.role}})
    return {"role": data.role}


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, admin=Depends(require_role(["admin"]))):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.get("/products")
async def admin_list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_role(["admin"])),
):
    skip = (page - 1) * limit
    total = await products_collection.count_documents({})
    products = await products_collection.find().sort("created_at", -1).skip(skip).to_list(length=limit)
    result = []
    for p in products:
        seller = await users_collection.find_one({"_id": ObjectId(p["seller_id"])}) if p.get("seller_id") else None
        result.append({
            "id": str(p["_id"]),
            "name": p.get("name", ""),
            "price": p.get("price", 0),
            "category": p.get("category", ""),
            "stock": p.get("stock", 0),
            "images": p.get("images", []),
            "description": p.get("description", ""),
            "seller_name": seller.get("name", "Unknown") if seller else "Unknown",
            "seller_email": seller.get("email", "") if seller else "",
            "shop_name": (seller.get("shop_name") or seller.get("store_name") or seller.get("shopName") or seller.get("name", "Unknown")) if seller else "Unknown",
            "created_at": str(p.get("created_at", "")),
        })
    return {"products": result, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}


@router.delete("/products/{product_id}")
async def admin_delete_product(product_id: str, admin=Depends(require_role(["admin"]))):
    result = await ProductModel.delete(product_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}


@router.put("/products/{product_id}")
async def admin_update_product(product_id: str, data: ProductUpdateData, admin=Depends(require_role(["admin"]))):
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    await ProductModel.update(product_id, update_data)
    return {"message": "Product updated"}


@router.get("/orders")
async def admin_list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    admin=Depends(require_role(["admin"])),
):
    query = {}
    if status:
        query["status"] = status
    skip = (page - 1) * limit
    total = await orders_collection.count_documents(query)
    orders = await orders_collection.find(query).sort("created_at", -1).skip(skip).to_list(length=limit)
    result = []
    for o in orders:
        buyer = await users_collection.find_one({"_id": ObjectId(o["buyer_id"])}) if o.get("buyer_id") else None
        result.append({
            "id": str(o["_id"]),
            "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
            "buyer_email": buyer.get("email", "") if buyer else "",
            "status": o.get("status", ""),
            "payment_status": o.get("payment_status", ""),
            "total": o.get("total", 0),
            "items": o.get("items", []),
            "created_at": str(o.get("created_at", "")),
        })
    return {"orders": result, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}


@router.delete("/orders/{order_id}")
async def admin_delete_order(order_id: str, admin=Depends(require_role(["admin"]))):
    result = await OrderModel.delete(order_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted"}


@router.patch("/orders/{order_id}/status")
async def admin_update_order_status(order_id: str, data: StatusUpdate, admin=Depends(require_role(["admin"]))):
    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid_statuses}")
    order = await OrderModel.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await OrderModel.update_status(order_id, data.status)
    return {"status": data.status}


@router.get("/dashboard-stats")
async def admin_dashboard_stats(admin=Depends(require_role(["admin"]))):
    total_users = await users_collection.count_documents({})
    total_products = await products_collection.count_documents({})
    total_orders = await orders_collection.count_documents({})
    total_riders = await users_collection.count_documents({"role": "rider"})
    total_sellers = await users_collection.count_documents({"role": "seller"})

    revenue_pipeline = [
        {"$match": {"status": "delivered"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
    ]
    revenue_result = await orders_collection.aggregate(revenue_pipeline).to_list(1)
    total_revenue = revenue_result[0]["total"] if revenue_result else 0
    pending_verifications = await users_collection.count_documents({"verification_status": "pending"})

    return {
        "users": total_users,
        "products": total_products,
        "orders": total_orders,
        "revenue": total_revenue,
        "riders": total_riders,
        "sellers": total_sellers,
        "pending_verifications": pending_verifications,
    }


@router.get("/analytics")
async def admin_analytics(admin=Depends(require_role(["admin"]))):
    from datetime import datetime, timedelta
    import calendar

    now = datetime.utcnow()
    monthly_data = []
    for i in range(6):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        start = datetime(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end = datetime(year, month, last_day, 23, 59, 59)

        pipeline = [
            {"$match": {"status": "delivered", "created_at": {"$gte": start, "$lte": end}}},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        result = await orders_collection.aggregate(pipeline).to_list(1)
        total = result[0]["total"] if result else 0

        monthly_data.append({
            "month": calendar.month_name[month],
            "revenue": total,
        })

    monthly_data.reverse()

    total_pipeline = [
        {"$match": {"status": "delivered"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
    ]
    total_result = await orders_collection.aggregate(total_pipeline).to_list(1)
    total_revenue_all = total_result[0]["total"] if total_result else 0

    return {
        "monthly": monthly_data,
        "total_revenue": total_revenue_all,
    }
