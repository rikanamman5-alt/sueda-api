from fastapi import APIRouter, HTTPException, Request
from services.paymaya_service import PayMayaService
from models.payment_model import PaymentModel
from services.payment_service import PaymentService

router = APIRouter(tags=["5. Payment"])


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
