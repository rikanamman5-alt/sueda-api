from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.delivery_fee_service import DeliveryFeeService

router = APIRouter(tags=["11. Delivery Fee"])


class FeeEstimateRequest(BaseModel):
    origin: str = ""
    destination: str = ""
    distance_km: Optional[float] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lng: Optional[float] = None


@router.post("/delivery/estimate-fee")
async def estimate_delivery_fee(body: FeeEstimateRequest):
    fee = DeliveryFeeService.compute_ai_fee(
        origin=body.origin,
        destination=body.destination,
        distance_km=body.distance_km,
        origin_lat=body.origin_lat,
        origin_lng=body.origin_lng,
        dest_lat=body.dest_lat,
        dest_lng=body.dest_lng,
    )
    return fee


@router.get("/delivery/location-fees")
async def get_location_fees():
    matrix = {}
    for (orig, dest), fee in DeliveryFeeService.LOCATION_FEES.items():
        key = f"{orig} -> {dest}"
        matrix[key] = fee
    return {"location_fees": matrix}
