from fastapi import APIRouter, HTTPException, Depends
from schemas.cart_schema import CartAddItem, CartUpdateItem
from services.cart_service import CartService
from utils.deps import get_current_user

router = APIRouter(tags=["3. Cart"])


@router.post("/cart/add")
async def add_to_cart(item: CartAddItem, user=Depends(get_current_user)):
    try:
        user_id = user.get("user_id") or user.get("email")
        return await CartService.add_item(user_id, item.product_id, item.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/cart/item/{product_id}")
async def remove_from_cart(product_id: str, user=Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("email")
    return await CartService.remove_item(user_id, product_id)


@router.put("/cart/item/{product_id}")
async def update_cart_item(product_id: str, body: CartUpdateItem, user=Depends(get_current_user)):
    try:
        user_id = user.get("user_id") or user.get("email")
        return await CartService.update_item_quantity(user_id, product_id, body.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cart")
async def get_cart(user=Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("email")
    return await CartService.get_cart(user_id)


@router.delete("/cart")
async def clear_cart(user=Depends(get_current_user)):
    user_id = user.get("user_id") or user.get("email")
    return await CartService.clear_cart(user_id)
