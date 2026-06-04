from fastapi import APIRouter, HTTPException, Depends, Body
from schemas.delivery_schema import DeliveryCreate
from services.delivery_service import DeliveryService
from utils.deps import require_role

router = APIRouter(tags=["6. Delivery"])


@router.post("/delivery/assign")
async def assign_rider(
    delivery: DeliveryCreate,
    admin=Depends(require_role(["admin", "seller"]))
):
    try:
        result = await DeliveryService.assign_rider(
            delivery.order_id, delivery.rider_id
        )
        return {
            "delivery_id": str(result.inserted_id) if result else None,
            "message": "Rider assigned",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/auto-assign/{order_id}")
async def auto_assign_rider(
    order_id: str,
    admin=Depends(require_role(["admin", "seller"])),
):
    from services.rider_service import RiderService
    try:
        result = await RiderService.auto_assign(order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/accept/{order_id}")
async def accept_delivery(
    order_id: str,
    rider=Depends(require_role(["rider"])),
):
    rider_id = rider.get("user_id")
    try:
        result = await DeliveryService.accept_assignment(order_id, rider_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/cancel-assignment/{order_id}")
async def cancel_assignment(
    order_id: str,
    admin=Depends(require_role(["admin", "seller"])),
):
    try:
        result = await DeliveryService.cancel_assignment(order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/reassign/{order_id}")
async def reassign_rider(
    order_id: str,
    admin=Depends(require_role(["admin", "seller"])),
):
    try:
        result = await DeliveryService.reassign_rider(order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/check-timeout/{order_id}")
async def check_timeout(order_id: str):
    try:
        result = await DeliveryService.process_expired(order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/delivery/timeouts")
async def get_timeouts(admin=Depends(require_role(["admin", "seller"]))):
    expired = await DeliveryService.check_timeouts()
    return {"expired_order_ids": expired}


@router.put("/delivery/location/{order_id}")
async def update_location(
    order_id: str,
    location: dict,
    rider=Depends(require_role(["rider"]))
):
    await DeliveryService.update_location(order_id, location)
    return {"message": "Location updated"}


@router.put("/delivery/status/{order_id}")
async def update_status(
    order_id: str,
    status: str = Body(..., embed=True),
    rider=Depends(require_role(["rider", "admin"]))
):
    try:
        await DeliveryService.update_status(order_id, status)
        return {"message": f"Status updated to {status}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/delivery/{order_id}")
async def get_delivery(order_id: str):
    delivery = await DeliveryService.get_by_order(order_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery
