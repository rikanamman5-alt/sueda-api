from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from bson.objectid import ObjectId
from services.paymaya_service import PayMayaService
from models.payment_model import PaymentModel
from services.payment_service import PaymentService
from utils.deps import get_current_user
from database.collections import users_collection, orders_collection

router = APIRouter(tags=["5. Payment"])


class PaymentConfirmRequest(BaseModel):
    order_id: str


@router.post("/api/payments/gcash", dependencies=[Depends(get_current_user)])
async def gcash_payment(data: PaymentConfirmRequest):
    order = await orders_collection.find_one({"_id": ObjectId(data.order_id)})
    seller_id = order.get("seller_id") if order else None
    seller = await users_collection.find_one({"email": seller_id}) if seller_id else None
    return {
        "gcashName": (seller.get("gcash_name") if seller else None) or "Sueda Store",
        "gcashNumber": (seller.get("gcash_number") if seller else None) or "09123456789",
    }


@router.post("/api/payments/credit-card", dependencies=[Depends(get_current_user)])
async def credit_card_payment(data: PaymentConfirmRequest):
    order = await orders_collection.find_one({"_id": ObjectId(data.order_id)})
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
async def create_payment(order_id: str, amount: float):
    checkout = PayMayaService.create_checkout(order_id, amount)
    await PaymentService.create_payment_record(
        order_id, amount, checkout.get("checkoutId")
    )
    return checkout


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
        return await PaymentService.process_success(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pay/fail")
async def payment_fail():
    return {"message": "Payment failed"}


@router.get("/pay/cancel")
async def payment_cancel():
    return {"message": "Payment cancelled"}
