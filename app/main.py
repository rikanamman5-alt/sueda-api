import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "app"))

import os
import jwt
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from core.config import BASE_DIR, SECRET_KEY, ALGORITHM
from controllers import (
    auth_controller, user_controller, order_controller, payment_controller,
    product_controller, delivery_controller, cart_controller, seller_controller,
    rider_controller, upload_controller, admin_controller, rating_controller,
    delivery_fee_controller, image_controller,
)
from routes import auth as auth_routes, upload as upload_routes
from database.mongo import db
from core.config import MONGO_URI, DB_NAME, CORS_ORIGINS, ADMIN_EMAIL, ADMIN_PASSWORD
from utils.jwt import hash_password
from services.websocket_manager import ws_manager

app = FastAPI(title="Sueda API", version="1.0.0")


@app.get("/")
def home():
    return {"message": "SUEDA API is running"}

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-change-this"),
    same_site="lax",
    https_only=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Validation failed"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)},
    )


@app.on_event("startup")
async def startup():
    print("[OK] MongoDB connected")
    await db.users.create_index("email", unique=True)
    await db.orders.create_index("buyer_id")
    await db.products.create_index("seller_id")
    await db.products.create_index("category")
    await db.deliveries.create_index("order_id", unique=True)
    await db.payments.create_index("order_id", unique=True)
    await db.carts.create_index("user_id", unique=True)
    await db.ratings.create_index(["product_id", "user_id"])
    print("[OK] Indexes created")

    # Auto-create/update admin user
    if ADMIN_EMAIL and ADMIN_PASSWORD:
        existing = await db.users.find_one({"email": ADMIN_EMAIL})
        if existing:
            update_data = {
                "role": "admin",
                "name": existing.get("name", "Admin"),
                "provider": "email",
            }
            if not existing.get("password_hash"):
                update_data["password_hash"] = hash_password(ADMIN_PASSWORD)
            await db.users.update_one(
                {"email": ADMIN_EMAIL},
                {"$set": update_data}
            )
            print("[OK] Admin user updated")
        else:
            hashed = hash_password(ADMIN_PASSWORD)
            await db.users.insert_one({
                "email": ADMIN_EMAIL,
                "password_hash": hashed,
                "name": "Admin",
                "provider": "email",
                "role": "admin",
            })
            print("[OK] Admin user created")
    else:
        print("[WARN] ADMIN_EMAIL or ADMIN_PASSWORD not set")


@app.on_event("shutdown")
async def shutdown():
    print("[OK] MongoDB disconnected")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query("")):
    user_email = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") == "access":
                user_email = payload.get("email") or payload.get("user_id")
        except Exception:
            pass

    if user_email:
        await ws_manager.connect_user(user_email, websocket)
        print(f"WebSocket user connected: {user_email}")
    else:
        await websocket.accept()
        print("WebSocket anonymous client connected")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if user_email:
            ws_manager.disconnect_user(user_email, websocket)
            print(f"WebSocket user disconnected: {user_email}")
        else:
            print("WebSocket anonymous client disconnected")


app.include_router(auth_routes.router)
app.include_router(auth_controller.router)
app.include_router(product_controller.router)
app.include_router(cart_controller.router)
app.include_router(order_controller.router)
app.include_router(payment_controller.router)
app.include_router(delivery_controller.router)
app.include_router(seller_controller.router)
app.include_router(rider_controller.router)
app.include_router(user_controller.router)
app.include_router(upload_controller.router)
app.include_router(upload_routes.router)
app.include_router(admin_controller.router)
app.include_router(rating_controller.router)
app.include_router(delivery_fee_controller.router)
app.include_router(image_controller.router)

static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(os.path.join(static_dir, "uploads"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

uploads_dir = os.path.join(BASE_DIR, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
