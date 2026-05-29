import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from jose import jwt, jwk, JWTError
from utils.jwt import create_access_token, create_refresh_token, hash_password, verify_password
from core.config import SECRET_KEY, ALGORITHM, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, ADMIN_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
from database.collections import users_collection
from utils.deps import get_current_user, require_role
from schemas.auth_schema import RegisterRequest, LoginRequest
import httpx
from bson.objectid import ObjectId

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_ISSUER = "https://accounts.google.com"

router = APIRouter(tags=["1. Auth"])


@router.get("/auth/google/callback")
async def google_callback(code: str):
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=data)
        token_json = token_res.json()

        if not token_json.get("access_token"):
            raise HTTPException(status_code=400, detail="Google token failed")

        # STEP 3: Validate id_token using Google's JWKS
        user_info = None
        id_token = token_json.get("id_token")
        if id_token:
            try:
                header = jwt.get_unverified_header(id_token)
                kid = header.get("kid")
                jwks_res = await client.get(GOOGLE_JWKS_URL)
                jwks = jwks_res.json()
                key_data = None
                for key in jwks.get("keys", []):
                    if key.get("kid") == kid:
                        key_data = key
                        break
                if key_data:
                    rsa_key = jwk.construct(key_data)
                    claims = jwt.decode(
                        id_token, rsa_key,
                        algorithms=["RS256"],
                        audience=GOOGLE_CLIENT_ID,
                        issuer=GOOGLE_ISSUER,
                    )
                    user_info = {
                        "email": claims.get("email"),
                        "name": claims.get("name", ""),
                        "picture": claims.get("picture", ""),
                    }
            except Exception:
                pass

        if not user_info:
            user_res = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token_json['access_token']}"}
            )
            user_info = user_res.json()

    user = await users_collection.find_one({"email": user_info["email"]})

    if not user:
        new_user = {
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture"),
            "provider": "google",
            "role": "user"
        }

        result = await users_collection.insert_one(new_user)
        user_id = str(result.inserted_id)
        role = "user"
    else:
        user_id = str(user["_id"])
        role = user.get("role", "user")

    access_token = create_access_token({
        "user_id": user_id,
        "email": user_info["email"],
        "role": role
    })

    refresh_token = create_refresh_token({
        "user_id": user_id,
        "email": user_info["email"],
        "role": role
    })

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": refresh_token}}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture")
        }
    }


@router.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload["user_id"]
        email = payload["email"]

        user = await users_collection.find_one({"_id": ObjectId(user_id)})

        if not user or user.get("refresh_token") != refresh_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        role = user.get("role", "user")

        new_access_token = create_access_token({
            "user_id": user_id,
            "email": email,
            "role": role
        })

        new_refresh_token = create_refresh_token({
            "user_id": user_id,
            "email": email,
            "role": role
        })

        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"refresh_token": new_refresh_token}}
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


from pydantic import BaseModel


class GoogleMobileAuth(BaseModel):
    access_token: str
    email: str
    name: str = ""


@router.post("/auth/google/mobile")
async def google_mobile_auth(data: GoogleMobileAuth):
    async with httpx.AsyncClient() as client:
        try:
            user_res = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {data.access_token}"}
            )
            if user_res.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google access token")
            user_info = {
                "email": user_res.json().get("email"),
                "name": user_res.json().get("name", data.name),
                "picture": user_res.json().get("picture", ""),
            }
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Failed to verify token with Google")

    user = await users_collection.find_one({"email": user_info["email"]})

    if not user:
        new_user = {
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture"),
            "provider": "google",
            "role": "buyer",
        }
        result = await users_collection.insert_one(new_user)
        user_id = str(result.inserted_id)
        role = "buyer"
    else:
        user_id = str(user["_id"])
        role = user.get("role", "buyer")

    access_token = create_access_token({
        "user_id": user_id,
        "email": user_info["email"],
        "role": role,
    })

    refresh_token = create_refresh_token({
        "user_id": user_id,
        "email": user_info["email"],
        "role": role,
    })

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": refresh_token}},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture"),
            "role": role,
        },
    }


@router.post("/auth/register")
async def register(data: RegisterRequest):
    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if ADMIN_EMAIL and data.email.lower() == ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="This email is reserved")

    role = data.role.lower()
    if role not in ("buyer", "seller", "rider"):
        raise HTTPException(status_code=400, detail="Invalid role. Choose buyer, seller, or rider")
    if role == "admin":
        raise HTTPException(status_code=403, detail="Admin registration not allowed")

    hashed = hash_password(data.password)
    new_user = {
        "email": data.email,
        "name": data.name,
        "password_hash": hashed,
        "provider": "email",
        "role": role,
        "address": data.address,
        "contact_number": data.contact_number,
    }

    if role == "seller":
        new_user["shop_description"] = ""

    if role == "rider":
        new_user["location"] = None
        new_user["is_available"] = True
        if data.license_number:
            new_user["license_number"] = data.license_number
        if data.vehicle_brand:
            new_user["vehicle_brand"] = data.vehicle_brand
        if data.vehicle_model:
            new_user["vehicle_model"] = data.vehicle_model
        if data.vehicle_plate:
            new_user["vehicle_plate"] = data.vehicle_plate
        if data.vehicle_color:
            new_user["vehicle_color"] = data.vehicle_color

    if role == "seller":
        if data.business_permit:
            new_user["business_permit"] = data.business_permit

    result = await users_collection.insert_one(new_user)
    user_id = str(result.inserted_id)

    access_token = create_access_token({
        "user_id": user_id, "email": data.email, "role": role,
    })
    refresh_token = create_refresh_token({
        "user_id": user_id, "email": data.email, "role": role,
    })

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": refresh_token}},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"email": data.email, "name": data.name, "role": role, "address": data.address, "contact_number": data.contact_number},
    }


@router.post("/auth/register/rider")
async def register_rider(data: RegisterRequest):
    if ADMIN_EMAIL and data.email.lower() == ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="This email is reserved")

    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(data.password)
    new_user = {
        "email": data.email,
        "name": data.name,
        "password_hash": hashed,
        "provider": "email",
        "role": "rider",
        "address": data.address,
        "contact_number": data.contact_number,
        "location": None,
        "is_available": True,
    }
    if data.license_number:
        new_user["license_number"] = data.license_number
    if data.vehicle_brand:
        new_user["vehicle_brand"] = data.vehicle_brand
    if data.vehicle_model:
        new_user["vehicle_model"] = data.vehicle_model
    if data.vehicle_plate:
        new_user["vehicle_plate"] = data.vehicle_plate
    if data.vehicle_color:
        new_user["vehicle_color"] = data.vehicle_color
    result = await users_collection.insert_one(new_user)
    user_id = str(result.inserted_id)
    role = "rider"

    access_token = create_access_token({
        "user_id": user_id, "email": data.email, "role": role,
    })
    refresh_token = create_refresh_token({
        "user_id": user_id, "email": data.email, "role": role,
    })

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": refresh_token}},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"email": data.email, "name": data.name, "role": role},
    }


@router.post("/auth/login")
async def login(data: LoginRequest):
    user = await users_collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    stored = user.get("password_hash")
    if not stored or not verify_password(data.password, stored):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user["_id"])
    role = "admin" if (ADMIN_EMAIL and data.email.lower() == ADMIN_EMAIL.lower()) else user.get("role", "buyer")
    name = user.get("name", "")

    access_token = create_access_token({
        "user_id": user_id, "email": data.email, "role": role,
    })
    refresh_token = create_refresh_token({
        "user_id": user_id, "email": data.email, "role": role,
    })

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": refresh_token}},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"email": data.email, "name": name, "role": role, "address": user.get("address", ""), "contact_number": user.get("contact_number", ""), "avatar": user.get("avatar")},
    }


@router.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    email = user.get("sub") or user.get("email")
    db_user = await users_collection.find_one({"email": email}, {"_id": 0, "password_hash": 0, "refresh_token": 0})
    if db_user:
        if db_user.get("avatar"):
            db_user["picture"] = db_user["avatar"]
        return {"message": "Access granted", "user": db_user}
    return {"message": "Access granted", "user": user}


@router.get("/auth/me")
async def get_me(user=Depends(get_current_user)):
    email = user.get("email")
    db_user = await users_collection.find_one(
        {"email": email},
        {"password_hash": 0, "refresh_token": 0}
    )
    if db_user:
        db_user["_id"] = str(db_user["_id"])
        return db_user
    return user


class UpdateRoleRequest(BaseModel):
    role: str


@router.patch("/auth/role")
async def update_role(data: UpdateRoleRequest, user=Depends(get_current_user)):
    valid_roles = {"buyer", "seller", "rider"}
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role. Choose buyer, seller, or rider")

    email = user.get("email")
    result = await users_collection.update_one(
        {"email": email},
        {"$set": {"role": data.role}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    new_access_token = create_access_token({
        "user_id": user.get("user_id"),
        "email": email,
        "role": data.role,
    })

    new_refresh_token = create_refresh_token({
        "user_id": user.get("user_id"),
        "email": email,
        "role": data.role,
    })

    await users_collection.update_one(
        {"email": email},
        {"$set": {"refresh_token": new_refresh_token}},
    )

    return {
        "message": "Role updated successfully",
        "role": data.role,
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.get("/user/dashboard")
def user_dashboard(user=Depends(require_role(["user"]))):
    return {"message": "Welcome USER dashboard"}


@router.get("/admin/dashboard")
def admin_dashboard(user=Depends(require_role(["admin"]))):
    return {"message": "Welcome ADMIN panel"}
