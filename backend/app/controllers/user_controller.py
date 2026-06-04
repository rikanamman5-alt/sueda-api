from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson.objectid import ObjectId
from models.user_model import UserModel
from models.product_model import ProductModel
from schemas.user_schema import UserCreate, UserUpdate
from utils.deps import get_current_user
from utils.jwt import create_access_token, create_refresh_token, hash_password, verify_password
from utils.mongo_helpers import fix_mongo
from datetime import datetime
from database.collections import users_collection

router = APIRouter(tags=["9. Users"])


class AccountSettingsUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    contact_number: str | None = None
    address: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def _require_same_user(email: str, current_user: dict):
    token_email = current_user.get("email") or current_user.get("user_id")
    if token_email != email:
        raise HTTPException(status_code=403, detail="Cannot access another user")


def _default_notifications():
    return [
        {
            "id": "welcome",
            "title": "Welcome to SUEDA",
            "message": "Track orders, save favorites, and check promos here.",
            "time": "Today",
            "read": False,
        },
        {
            "id": "promo_flash_sale",
            "title": "Flash Sale",
            "message": "Tap Flash Sale on the home page to browse sale picks.",
            "time": "Today",
            "read": False,
        },
    ]


@router.post("/users")
async def create_user(data: UserCreate):
    existing = await UserModel.get_user(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    await UserModel.create_user(data.model_dump())
    return {"message": "User created"}


@router.get("/users/{email}")
async def get_user(email: str):
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{email}")
async def update_user(
    email: str,
    data: UserUpdate,
    current_user=Depends(get_current_user),
):
    token_email = current_user.get("email") or current_user.get("user_id")
    if token_email != email:
        raise HTTPException(status_code=403, detail="Cannot update another user")

    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await UserModel.update_user(email, update_data)
    return {"message": "User updated"}


@router.put("/users/account/settings")
async def update_account_settings(
    data: AccountSettingsUpdate,
    current_user=Depends(get_current_user),
):
    current_email = current_user.get("email") or current_user.get("user_id")
    user = await users_collection.find_one({"email": current_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("role") in {"seller", "rider"} and user.get("verification_status") != "verified":
        raise HTTPException(
            status_code=403,
            detail="You need to be verified within 24 hours before updating account information.",
        )

    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name.strip()
    if data.contact_number is not None:
        update_data["contact_number"] = data.contact_number.strip()
    if data.address is not None:
        update_data["address"] = data.address.strip()

    new_email = data.email.strip().lower() if data.email else None
    email_changed = bool(new_email and new_email != current_email)
    wants_password_change = bool(data.new_password)

    if email_changed or wants_password_change:
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        stored = user.get("password_hash")
        if not stored or not verify_password(data.current_password, stored):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

    if email_changed:
        existing = await users_collection.find_one({"email": new_email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        update_data["email"] = new_email

    if wants_password_change:
        if len(data.new_password or "") < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        update_data["password_hash"] = hash_password(data.new_password)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await users_collection.update_one({"email": current_email}, {"$set": update_data})

    final_email = update_data.get("email", current_email)
    response = {"message": "Account settings updated", "email": final_email}
    if email_changed:
        token_data = {
            "user_id": str(user["_id"]),
            "email": final_email,
            "role": user.get("role", current_user.get("role", "buyer")),
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        await users_collection.update_one(
            {"email": final_email},
            {"$set": {"refresh_token": refresh_token}},
        )
        response.update({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        })
    return response


@router.delete("/users/{email}")
async def delete_user(
    email: str,
    current_user=Depends(get_current_user),
):
    token_email = current_user.get("email") or current_user.get("user_id")
    if token_email != email:
        raise HTTPException(status_code=403, detail="Cannot delete another user")

    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await UserModel.delete_user(email)
    return {"message": "User deleted"}


@router.get("/users/{email}/wishlist")
async def get_wishlist(email: str, current_user=Depends(get_current_user)):
    _require_same_user(email, current_user)
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    wishlist_ids = user.get("wishlist", [])
    products = []
    for product_id in wishlist_ids:
        try:
            product = await ProductModel.get_by_id(product_id)
            if product:
                products.append(fix_mongo(product))
        except Exception:
            pass
    return {"wishlist": products}


@router.post("/users/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, current_user=Depends(get_current_user)):
    email = current_user.get("email") or current_user.get("user_id")
    product = await ProductModel.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await UserModel.add_to_wishlist(email, product_id)
    return {"message": "Added to wishlist"}


@router.delete("/users/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, current_user=Depends(get_current_user)):
    email = current_user.get("email") or current_user.get("user_id")
    await UserModel.remove_from_wishlist(email, product_id)
    return {"message": "Removed from wishlist"}


@router.get("/users/{email}/notifications")
async def get_notifications(email: str, current_user=Depends(get_current_user)):
    _require_same_user(email, current_user)
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"notifications": user.get("notifications") or _default_notifications()}


@router.patch("/users/notification/{notification_id}")
async def mark_notification_read(
    notification_id: str,
    data: dict,
    current_user=Depends(get_current_user),
):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    notifications = user.get("notifications") or _default_notifications()
    for notification in notifications:
        if str(notification.get("id") or notification.get("_id")) == notification_id:
            notification["read"] = bool(data.get("read", True))
    await UserModel.update_user(email, {"notifications": notifications})
    return {"message": "Notification updated"}


@router.patch("/users/notifications/read-all")
async def mark_all_notifications_read(current_user=Depends(get_current_user)):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    notifications = user.get("notifications") or []
    for notification in notifications:
        notification["read"] = True
    await UserModel.update_user(email, {"notifications": notifications})
    return {"message": "All notifications marked as read"}


@router.put("/users/{email}/notification-settings")
async def update_notification_settings(
    email: str,
    data: dict,
    current_user=Depends(get_current_user),
):
    _require_same_user(email, current_user)
    await UserModel.update_user(email, {"notification_settings": data})
    return {"message": "Notification settings updated"}


class PaymentMethodCreate(BaseModel):
    type: str
    label: str
    details: str


@router.get("/users/{email}/payment-methods")
async def get_payment_methods(email: str, current_user=Depends(get_current_user)):
    _require_same_user(email, current_user)
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"payment_methods": user.get("payment_methods", [])}


@router.post("/users/{email}/payment-methods")
async def add_payment_method(
    email: str,
    data: PaymentMethodCreate,
    current_user=Depends(get_current_user),
):
    _require_same_user(email, current_user)
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    methods = user.get("payment_methods", [])
    new_method = {
        "_id": str(ObjectId()),
        "type": data.type,
        "label": data.label,
        "details": data.details,
    }
    methods.append(new_method)
    await users_collection.update_one({"email": email}, {"$set": {"payment_methods": methods}})
    return {"message": "Payment method added", "payment_method": new_method}


@router.put("/users/payment-method/{method_id}")
async def update_payment_method(
    method_id: str,
    data: PaymentMethodCreate,
    current_user=Depends(get_current_user),
):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    methods = user.get("payment_methods", [])
    for m in methods:
        if str(m.get("_id") or m.get("id")) == method_id:
            m["type"] = data.type
            m["label"] = data.label
            m["details"] = data.details
            break
    else:
        raise HTTPException(status_code=404, detail="Payment method not found")
    await users_collection.update_one({"email": email}, {"$set": {"payment_methods": methods}})
    return {"message": "Payment method updated"}


@router.delete("/users/payment-method/{method_id}")
async def delete_payment_method(method_id: str, current_user=Depends(get_current_user)):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    methods = user.get("payment_methods", [])
    methods = [m for m in methods if str(m.get("_id") or m.get("id")) != method_id]
    await users_collection.update_one({"email": email}, {"$set": {"payment_methods": methods}})
    return {"message": "Payment method deleted"}


@router.post("/users/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user=Depends(get_current_user),
):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    stored = user.get("password_hash")
    if not stored or not verify_password(data.current_password, stored):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    await users_collection.update_one(
        {"email": email},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    return {"message": "Password changed successfully"}


@router.get("/users/{email}/addresses")
async def get_addresses(email: str, current_user=Depends(get_current_user)):
    _require_same_user(email, current_user)
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"addresses": user.get("addresses", [])}


@router.post("/users/{email}/addresses")
async def add_address(
    email: str,
    data: dict,
    current_user=Depends(get_current_user),
):
    _require_same_user(email, current_user)
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    addresses = user.get("addresses", [])
    new_addr = {
        "_id": str(ObjectId()),
        "label": data.get("label", ""),
        "full_name": data.get("full_name", ""),
        "phone": data.get("phone", ""),
        "address": data.get("address", ""),
        "is_default": data.get("is_default", False),
    }
    addresses.append(new_addr)
    await users_collection.update_one({"email": email}, {"$set": {"addresses": addresses}})
    return {"message": "Address added", "address": new_addr}


@router.put("/users/address/{address_id}")
async def update_address(
    address_id: str,
    data: dict,
    current_user=Depends(get_current_user),
):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    addresses = user.get("addresses", [])
    for addr in addresses:
        if str(addr.get("_id") or addr.get("id")) == address_id:
            if "label" in data: addr["label"] = data["label"]
            if "full_name" in data: addr["full_name"] = data["full_name"]
            if "phone" in data: addr["phone"] = data["phone"]
            if "address" in data: addr["address"] = data["address"]
            if "is_default" in data: addr["is_default"] = data["is_default"]
            break
    else:
        raise HTTPException(status_code=404, detail="Address not found")
    await users_collection.update_one({"email": email}, {"$set": {"addresses": addresses}})
    return {"message": "Address updated"}


@router.delete("/users/address/{address_id}")
async def delete_address(address_id: str, current_user=Depends(get_current_user)):
    email = current_user.get("email") or current_user.get("user_id")
    user = await UserModel.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    addresses = user.get("addresses", [])
    addresses = [a for a in addresses if str(a.get("_id") or a.get("id")) != address_id]
    await users_collection.update_one({"email": email}, {"$set": {"addresses": addresses}})
    return {"message": "Address deleted"}


@router.post("/users/{email}/support")
async def submit_support_ticket(
    email: str,
    data: dict,
    current_user=Depends(get_current_user),
):
    _require_same_user(email, current_user)
    ticket = {
        "_id": str(ObjectId()),
        "email": email,
        "subject": data.get("subject", ""),
        "message": data.get("message", ""),
        "created_at": datetime.utcnow(),
        "status": "open",
    }
    await users_collection.update_one(
        {"email": email},
        {"$push": {"support_tickets": ticket}}
    )
    return {"message": "Support ticket submitted successfully"}
