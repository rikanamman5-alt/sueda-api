from pydantic import BaseModel
from typing import Optional


class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: float


class OrderCreate(BaseModel):
    buyer_id: str
    seller_id: str
    items: list[OrderItem]
    delivery_address: str = ""
    buyer_contact: str = ""
    buyer_lat: Optional[float] = None
    buyer_lng: Optional[float] = None
    payment_method: Optional[str] = None
    delivery_fee: Optional[float] = None
