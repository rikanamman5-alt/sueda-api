from pydantic import BaseModel


class CartItem(BaseModel):
    product_id: str
    quantity: int


class CartAddItem(BaseModel):
    product_id: str
    quantity: int = 1


class CartUpdateItem(BaseModel):
    quantity: int
