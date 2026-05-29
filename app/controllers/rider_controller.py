from bson.objectid import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional
from database.collections import users_collection, deliveries_collection
from models.delivery_model import DeliveryModel
from models.order_model import OrderModel
from utils.deps import require_role, get_current_user
from utils.mongo_helpers import fix_mongo


class RiderVerificationRequest(BaseModel):
    vehicle_brand: str
    vehicle_model: str
    vehicle_plate: str
    vehicle_color: str
    verification_doc: Optional[str] = None

router = APIRouter(tags=["8. Rider"])


async def _require_verified_rider(email: str):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("verification_status") != "verified":
        raise HTTPException(
            status_code=403,
            detail="You need to be verified within 24 hours before using rider features.",
        )
    return user


@router.put("/rider/location")
async def update_rider_location(
    location: dict,
    rider=Depends(require_role(["rider"])),
):
    email = rider.get("sub") or rider.get("email")
    await _require_verified_rider(email)
    await users_collection.update_one(
        {"email": email},
        {"$set": {"location": location}},
    )
    return {"message": "Location updated"}


@router.get("/rider/deliveries")
async def get_rider_deliveries(rider=Depends(require_role(["rider"]))):
    email = rider.get("sub") or rider.get("email")
    await _require_verified_rider(email)
    rider_id = rider.get("user_id")
    deliveries = await DeliveryModel.get_by_rider(rider_id)

    result = []
    for d in deliveries:
        order = await OrderModel.get_by_id(d["order_id"])
        if order:
            seller = None
            seller_id = order.get("seller_id")
            if seller_id:
                seller = await users_collection.find_one({"_id": ObjectId(seller_id) if isinstance(seller_id, str) else seller_id})
            buyer = None
            buyer_id = order.get("buyer_id")
            if buyer_id:
                buyer = await users_collection.find_one({"_id": ObjectId(buyer_id) if isinstance(buyer_id, str) else buyer_id})
            assigned_rider = None
            rider_id = d.get("rider_id")
            if rider_id:
                assigned_rider = await users_collection.find_one({"_id": ObjectId(rider_id) if isinstance(rider_id, str) else rider_id})
            result.append({
                "delivery": fix_mongo(d),
                "order": fix_mongo(order),
                "seller": fix_mongo(seller) if seller else None,
                "buyer": fix_mongo(buyer) if buyer else None,
                "assigned_rider": fix_mongo(assigned_rider) if assigned_rider else None,
            })

    return {"deliveries": result}


@router.get("/riders")
async def get_all_riders(user=Depends(get_current_user)):
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
        r["_id"] = rider_id
        r["active_deliveries"] = active_count
        r["rider_status"] = r.get(
            "rider_status",
            "available" if active_count == 0 else "delivering",
        )
        r["current_order_id"] = r.get("current_order_id")
        result.append(r)
    return {"riders": result}


@router.put("/rider/verification")
async def submit_rider_verification(
    data: RiderVerificationRequest,
    rider=Depends(require_role(["rider"])),
):
    email = rider.get("sub") or rider.get("email")
    update = {
        "vehicle_brand": data.vehicle_brand,
        "vehicle_model": data.vehicle_model,
        "vehicle_plate": data.vehicle_plate,
        "vehicle_color": data.vehicle_color,
        "verification_status": "pending",
        "verification_reject_reason": "",
    }
    if data.verification_doc:
        update["verification_doc"] = data.verification_doc
    await users_collection.update_one({"email": email}, {"$set": update})
    return {"message": "Verification submitted for review"}


@router.put("/rider/delivery/{order_id}/status")
async def update_delivery_status(
    order_id: str,
    status: str = Body(..., embed=True),
    rider=Depends(require_role(["rider"])),
):
    email = rider.get("sub") or rider.get("email")
    await _require_verified_rider(email)
    from services.delivery_service import DeliveryService
    try:
        await DeliveryService.update_status(order_id, status)
        return {"message": f"Delivery status updated to {status}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/rider/deliveries/{order_id}")
async def remove_rider_delivery(
    order_id: str,
    rider=Depends(require_role(["rider"])),
):
    rider_id = rider.get("user_id")
    delivery = await DeliveryModel.get_by_order(order_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if delivery.get("rider_id") != rider_id:
        raise HTTPException(status_code=403, detail="Not your delivery")
    await DeliveryModel.delete_by_order(order_id)
    return {"message": "Delivery removed"}


@router.post("/rider/delivery/{order_id}/accept")
async def accept_delivery(
    order_id: str,
    rider=Depends(require_role(["rider"])),
):
    email = rider.get("sub") or rider.get("email")
    await _require_verified_rider(email)
    rider_id = rider.get("user_id")
    from services.delivery_service import DeliveryService
    try:
        result = await DeliveryService.accept_assignment(order_id, rider_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
