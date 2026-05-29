from pydantic import BaseModel
from typing import Optional


class Location(BaseModel):
    lat: float
    lng: float


class DeliveryCreate(BaseModel):
    order_id: str
    rider_id: str
    location: Optional[Location] = None


class RiderRegister(BaseModel):
    email: str
    password: str
    name: str
    contact_number: str = ""
    lat: float
    lng: float
