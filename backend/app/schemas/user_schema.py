from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    email: str
    name: str
    avatar: str | None = None
    address: str = ""
    contact_number: str = ""


class VerificationData(BaseModel):
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_color: Optional[str] = None
    business_permit: Optional[str] = None
    operating_hours: Optional[str] = None
    verification_doc: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    license_number: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_color: Optional[str] = None
    business_permit: Optional[str] = None
    operating_hours: Optional[str] = None
    verification_doc: Optional[str] = None
