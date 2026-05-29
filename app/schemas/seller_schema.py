from pydantic import BaseModel
from typing import Optional


class SellerProfileUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    shop_logo: Optional[str] = None
    shop_banner: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    shop_lat: Optional[float] = None
    shop_lng: Optional[float] = None
    gcash_name: Optional[str] = None
    gcash_number: Optional[str] = None
    card_number: Optional[str] = None
    card_holder_name: Optional[str] = None
    card_expiry: Optional[str] = None
    business_permit: Optional[str] = None
    operating_hours: Optional[str] = None
    verification_doc: Optional[str] = None
