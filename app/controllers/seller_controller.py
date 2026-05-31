from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from models.user_model import UserModel
from models.product_model import ProductModel
from models.order_model import OrderModel
from models.delivery_model import DeliveryModel
from schemas.seller_schema import SellerProfileUpdate
from schemas.product_schema import ProductCreate, ProductUpdate
from schemas.auth_schema import RegisterRequest
from utils.deps import require_role
from database.collections import users_collection, orders_collection, deliveries_collection
from utils.jwt import create_access_token, create_refresh_token, hash_password
from bson.objectid import ObjectId

router = APIRouter(tags=["7. Seller"])


class OrderStatusUpdate(BaseModel):
    status: str


class PaymentStatusUpdate(BaseModel):
    payment_status: str


class SellerVerificationRequest(BaseModel):
    business_permit: str
    operating_hours: str
    verification_doc: Optional[str] = None


async def _require_verified_seller(email: str):
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("verification_status") != "verified":
        raise HTTPException(
            status_code=403,
            detail="You need to be verified within 24 hours before using seller features.",
        )
    return user


@router.get("/seller/profile")
async def get_seller_profile(seller=Depends(require_role(["seller"]))):
    email = seller.get("sub") or seller.get("email")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "email": user.get("email"),
        "name": user.get("name"),
        "avatar": user.get("avatar"),
        "shop_name": user.get("shop_name"),
        "shop_description": user.get("shop_description"),
        "shop_logo": user.get("shop_logo"),
        "shop_banner": user.get("shop_banner"),
        "contact_email": user.get("contact_email"),
        "contact_phone": user.get("contact_phone"),
        "shop_lat": user.get("shop_lat"),
        "shop_lng": user.get("shop_lng"),
        "gcash_name": user.get("gcash_name"),
        "gcash_number": user.get("gcash_number"),
        "card_number": user.get("card_number"),
        "card_holder_name": user.get("card_holder_name"),
        "card_expiry": user.get("card_expiry"),
    }


@router.put("/seller/profile")
async def update_seller_profile(
    data: SellerProfileUpdate,
    seller=Depends(require_role(["seller"])),
):
    email = seller.get("sub") or seller.get("email")
    await _require_verified_seller(email)
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    await UserModel.update_user(email, update_data)
    return {"message": "Seller profile updated"}


@router.get("/seller/products")
async def get_seller_products(seller=Depends(require_role(["seller"]))):
    seller_id = seller.get("user_id")
    products = await ProductModel.get_by_seller(seller_id)
    result = []
    for p in products:
        result.append({
            "id": str(p["_id"]),
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "price": p.get("price", 0),
            "stock": p.get("stock", 0),
            "category": p.get("category", ""),
            "images": p.get("images", []),
            "created_at": str(p.get("created_at", "")),
        })
    return {"products": result}


@router.post("/seller/products")
async def create_seller_product(
    data: ProductCreate,
    seller=Depends(require_role(["seller"])),
):
    email = seller.get("sub") or seller.get("email")
    await _require_verified_seller(email)
    product = data.model_dump()
    product["seller_id"] = seller["user_id"]
    product["created_at"] = datetime.utcnow()
    result = await ProductModel.create(product)
    return {"product_id": str(result.inserted_id)}


@router.put("/seller/products/{product_id}")
async def update_seller_product(
    product_id: str,
    data: ProductUpdate,
    seller=Depends(require_role(["seller"])),
):
    email = seller.get("sub") or seller.get("email")
    await _require_verified_seller(email)
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(product.get("seller_id")) != seller["user_id"]:
        raise HTTPException(status_code=403, detail="Not your product")
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    await ProductModel.update(product_id, update_data)
    return {"message": "Product updated"}


@router.delete("/seller/products/{product_id}")
async def delete_seller_product(
    product_id: str,
    seller=Depends(require_role(["seller"])),
):
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(product.get("seller_id")) != seller["user_id"]:
        raise HTTPException(status_code=403, detail="Not your product")
    await ProductModel.delete(product_id)
    return {"message": "Product deleted"}


@router.get("/seller/dashboard")
async def get_seller_dashboard(seller=Depends(require_role(["seller"]))):
    seller_id = seller.get("user_id")
    products = await ProductModel.get_by_seller(seller_id)
    seller_email = seller.get("sub") or seller.get("email")
    user = await UserModel.get_user(seller_email)

    riders = await users_collection.find({
        "role": "rider",
        "seller_id": seller_id,
    }).to_list(100)
    available_riders = [r for r in riders if r.get("is_available")]

    orders = await orders_collection.find({"seller_id": seller_id}).to_list(500)
    total_orders = len(orders)
    pending_orders = len([o for o in orders if o.get("status") == "pending"])
    processing_orders = len([o for o in orders if o.get("status") == "processing"])
    shipped_orders = len([o for o in orders if o.get("status") == "shipped"])
    completed_orders = len([o for o in orders if o.get("status") == "delivered"])
    cancelled_orders = len([o for o in orders if o.get("status") == "cancelled"])

    total_revenue = sum(o.get("total_price", 0) for o in orders if o.get("status") == "delivered")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = [
        o for o in orders
        if isinstance(o.get("created_at"), datetime)
        and o["created_at"] >= today_start
    ]
    today_sales = sum(o.get("total_price", 0) for o in today_orders)

    total_products = len(products)
    low_stock = len([p for p in products if p.get("stock", 0) <= 5])
    
    rider_list = []
    for r in riders:
        rider_list.append({
            "name": r.get("name", ""),
            "email": r.get("email", ""),
            "contact_number": r.get("contact_number", ""),
            "is_available": r.get("is_available", True),
            "location": r.get("location"),
        })

    recent = sorted(orders, key=lambda o: o.get("created_at", datetime.min), reverse=True)[:10]
    recent_orders = []
    for o in recent:
        buyer = None
        if o.get("buyer_id"):
            try:
                buyer = await users_collection.find_one({"_id": ObjectId(o["buyer_id"])})
            except:
                pass
            if not buyer:
                buyer = await users_collection.find_one({"_id": o["buyer_id"]})
        recent_orders.append({
            "id": str(o["_id"]),
            "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
            "status": o.get("status", ""),
            "total": o.get("total_price", 0),
            "delivery_fee": o.get("delivery_fee", 0),
            "delivery_distance_km": o.get("delivery_distance_km"),
            "items": o.get("items", []),
            "created_at": str(o.get("created_at", "")),
        })

    return {
        "shop_name": user.get("shop_name", "My Shop"),
        "shop_address": user.get("address", ""),
        "shop_lat": user.get("shop_lat"),
        "shop_lng": user.get("shop_lng"),
        "riders": rider_list,
        "stats": {
            "total_products": total_products,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "processing_orders": processing_orders,
            "shipped_orders": shipped_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": total_revenue,
            "today_sales": today_sales,
            "low_stock": low_stock,
        },
        "total_riders": len(riders),
        "available_riders": len(available_riders),
        "recent_orders": recent_orders,
    }


@router.put("/seller/verification")
async def submit_seller_verification(
    data: SellerVerificationRequest,
    seller=Depends(require_role(["seller"])),
):
    email = seller.get("sub") or seller.get("email")
    update = {
        "business_permit": data.business_permit,
        "operating_hours": data.operating_hours,
        "verification_status": "pending",
        "verification_reject_reason": "",
    }
    if data.verification_doc:
        update["verification_doc"] = data.verification_doc
    await users_collection.update_one({"email": email}, {"$set": update})
    return {"message": "Verification submitted for review"}


@router.get("/seller/orders")
async def get_seller_orders(seller=Depends(require_role(["seller"]))):
    seller_id = seller.get("user_id")
    orders = await orders_collection.find({"seller_id": seller_id}).sort("created_at", -1).to_list(200)
    result = []
    for o in orders:
        buyer = None
        if o.get("buyer_id"):
            try:
                buyer = await users_collection.find_one({"_id": ObjectId(o["buyer_id"])})
            except:
                pass
            if not buyer:
                buyer = await users_collection.find_one({"_id": o["buyer_id"]})

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

        rider_name = None
        rider_id = o.get("rider_id")
        if rider_id:
            try:
                rider = await users_collection.find_one({"_id": ObjectId(rider_id)})
                if not rider:
                    rider = await users_collection.find_one({"_id": rider_id})
                if rider:
                    rider_name = rider.get("name", "")
            except Exception:
                pass

        delivery_status = o.get("delivery_status")
        if not delivery_status:
            delivery_doc = await DeliveryModel.get_by_order(str(o["_id"]))
            if delivery_doc:
                delivery_status = delivery_doc.get("status")

        result.append({
            "_id": str(o["_id"]),
            "buyer_id": str(o.get("buyer_id", "")),
            "seller_id": seller_id,
            "buyer_name": buyer.get("name", "Unknown") if buyer else "Unknown",
            "buyer_email": buyer.get("email", "") if buyer else "",
            "status": o.get("status", ""),
            "payment_status": o.get("payment_status", ""),
            "payment_method": o.get("payment_method"),
            "delivery_status": delivery_status,
            "subtotal": o.get("subtotal", 0),
            "delivery_fee": o.get("delivery_fee", 0),
            "total_price": o.get("total_price", 0),
            "delivery_distance_km": o.get("delivery_distance_km"),
            "items": items,
            "delivery_address": o.get("delivery_address", ""),
            "buyer_lat": o.get("buyer_lat"),
            "buyer_lng": o.get("buyer_lng"),
            "rider_id": rider_id,
            "rider": {"name": rider_name} if rider_name else None,
            "created_at": str(o.get("created_at", "")),
        })
    return {"orders": result}


@router.patch("/seller/orders/{order_id}/payment")
async def update_seller_order_payment(
    order_id: str,
    data: PaymentStatusUpdate,
    seller=Depends(require_role(["seller"])),
):
    order = await OrderModel.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(order.get("seller_id")) != seller["user_id"]:
        raise HTTPException(status_code=403, detail="Not your order")

    await OrderModel.update_payment_status(order_id, data.payment_status)
    if data.payment_status == "paid" and order.get("status") in ("pending", "processing", "Processing"):
        await OrderModel.update_status(order_id, "paid")
    return {"payment_status": data.payment_status}


@router.patch("/seller/orders/{order_id}/status")
async def update_seller_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    seller=Depends(require_role(["seller"])),
):
    valid = ["accepted", "processing", "shipped", "delivered", "cancelled"]
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid. Valid: {valid}")
    
    order = await OrderModel.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(order.get("seller_id")) != seller["user_id"]:
        raise HTTPException(status_code=403, detail="Not your order")

    await OrderModel.update_status(order_id, data.status)
    return {"status": data.status}


@router.post("/seller/riders")
async def register_seller_rider(
    data: RegisterRequest,
    seller=Depends(require_role(["seller"])),
):
    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    seller_id = seller.get("user_id")
    hashed = hash_password(data.password)
    new_rider = {
        "email": data.email,
        "name": data.name,
        "password_hash": hashed,
        "provider": "email",
        "role": "rider",
        "seller_id": seller_id,
        "address": data.address,
        "contact_number": data.contact_number,
        "location": None,
        "is_available": True,
    }
    await users_collection.insert_one(new_rider)
    return {"message": "Rider registered successfully"}


@router.get("/seller/riders")
async def get_seller_riders(seller=Depends(require_role(["seller"]))):
    riders = await users_collection.find(
        {"role": "rider"},
        {"password_hash": 0, "refresh_token": 0},
    ).to_list(200)
    active_statuses = {"assigned", "accepted", "picked_up", "in_transit"}
    result = []
    for r in riders:
        rider_id = str(r["_id"])
        active_count = await deliveries_collection.count_documents({
            "rider_id": rider_id,
            "status": {"$in": list(active_statuses)},
        })
        result.append({
            "_id": rider_id,
            "email": r.get("email"),
            "name": r.get("name"),
            "contact_number": r.get("contact_number", ""),
            "is_available": r.get("is_available", active_count == 0),
            "rider_status": r.get("rider_status", "available" if active_count == 0 else "delivering"),
            "current_order_id": r.get("current_order_id"),
            "active_deliveries": active_count,
            "location": r.get("location"),
        })
    return {"riders": result}


@router.delete("/seller/riders/{email}")
async def delete_seller_rider(
    email: str,
    seller=Depends(require_role(["seller"])),
):
    seller_id = seller.get("user_id")
    rider = await users_collection.find_one({"email": email, "seller_id": seller_id})
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    await users_collection.delete_one({"email": email})
    return {"message": "Rider removed"}
