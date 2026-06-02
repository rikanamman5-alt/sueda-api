from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from bson.objectid import ObjectId
from starlette.responses import RedirectResponse

from services.paymaya_service import PayMayaService
from models.payment_model import PaymentModel
from models.order_model import OrderModel
from services.payment_service import PaymentService
from utils.deps import get_current_user
from database.collections import users_collection, orders_collection
from core.config import BASE_DIR

router = APIRouter(tags=["5. Payment"])


class PaymentConfirmRequest(BaseModel):
    order_id: str


async def _find_order(order_id: str):
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        order = await orders_collection.find_one({"_id": order_id})
    return order


@router.post("/api/payments/gcash", dependencies=[Depends(get_current_user)])
async def gcash_payment(data: PaymentConfirmRequest):
    order = await _find_order(data.order_id)
    seller_id = order.get("seller_id") if order else None
    seller = await users_collection.find_one({"email": seller_id}) if seller_id else None
    return {
        "gcashName": (seller.get("gcash_name") if seller else None) or "Sueda Store",
        "gcashNumber": (seller.get("gcash_number") if seller else None) or "09123456789",
    }


@router.post("/api/payments/credit-card", dependencies=[Depends(get_current_user)])
async def credit_card_payment(data: PaymentConfirmRequest):
    order = await _find_order(data.order_id)
    seller_id = order.get("seller_id") if order else None
    seller = await users_collection.find_one({"email": seller_id}) if seller_id else None
    return {
        "cardNumber": (seller.get("card_number") if seller else None) or "1234 5678 9012 3456",
        "cardHolderName": (seller.get("card_holder_name") if seller else None) or "SUEDA STORE",
        "cardExpiry": (seller.get("card_expiry") if seller else None) or "12/28",
    }


@router.put("/api/payments/gcash/confirm", dependencies=[Depends(get_current_user)])
async def confirm_gcash(data: PaymentConfirmRequest):
    return {"message": "GCash payment confirmed"}


@router.put("/api/payments/credit-card/confirm", dependencies=[Depends(get_current_user)])
async def confirm_card(data: PaymentConfirmRequest):
    return {"message": "Card payment confirmed"}


@router.post("/pay/create/{order_id}")
async def create_payment(order_id: str):
    order = await _find_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    amount = float(order.get("total_price", 0))
    items = order.get("items", [])

    checkout = PayMayaService.create_checkout(
        order_id=order_id,
        amount=amount,
        items=[
            {
                "name": item.get("product_name", f"Item"),
                "quantity": item.get("quantity", 1),
                "amount": float(item.get("price", 0)),
            }
            for item in items
        ],
        redirect_base="https://sueda-api-1.onrender.com",
    )

    checkout_id = checkout.get("checkoutId")
    if checkout_id:
        await PaymentService.create_payment_record(order_id, amount, checkout_id)

    redirect_url = checkout.get("redirectUrl", {}).get(
        "checkoutUrl", checkout.get("checkoutUrl")
    )

    return {
        "checkout_url": redirect_url or checkout.get("redirectUrl", {}).get("url"),
        "checkout_id": checkout_id,
    }


@router.get("/pay/status/{order_id}")
async def get_payment_status(order_id: str):
    payment = await PaymentModel.get_by_order(order_id)
    order = await _find_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "payment_status": order.get("payment_status", "unpaid"),
        "order_status": order.get("status", "pending"),
    }


@router.post("/pay/webhook")
async def payment_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-PayMaya-Signature", "")

    if not PayMayaService.verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    try:
        result = await PaymentService.handle_webhook(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pay/success")
async def payment_success(order_id: str):
    try:
        result = await PaymentService.process_success(order_id)
        return RedirectResponse(
            url=f"https://sueda-api-1.onrender.com/pay/result?order_id={order_id}&status=success"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pay/fail")
async def payment_fail(order_id: str = None):
    if order_id:
        return RedirectResponse(
            url=f"https://sueda-api-1.onrender.com/pay/result?order_id={order_id}&status=failed"
        )
    return {"message": "Payment failed"}


@router.get("/pay/cancel")
async def payment_cancel(order_id: str = None):
    if order_id:
        return RedirectResponse(
            url=f"https://sueda-api-1.onrender.com/pay/result?order_id={order_id}&status=cancelled"
        )
    return {"message": "Payment cancelled"}


@router.get("/pay/result")
async def payment_result(order_id: str = None, status: str = None):
    return {"order_id": order_id, "status": status}
