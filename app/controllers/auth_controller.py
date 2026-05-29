import urllib.parse
from datetime import datetime
from fastapi import APIRouter, Request
from services.oauth_service import oauth
from models.user_model import UserModel
from utils.jwt import create_access_token, create_refresh_token
from core.config import GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI

router = APIRouter(tags=["1. Auth"])


@router.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@router.get("/auth/google")
async def auth_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    email = user_info["email"]

    existing_user = await UserModel.get_user(email)

    if not existing_user:
        new_user = {
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "provider": "google",
            "role": "buyer",
            "is_verified": True,
            "last_login": datetime.utcnow(),
        }
        result = await UserModel.create_user(new_user)
        user_id = str(result.inserted_id)
        role = "buyer"
    else:
        user_id = str(existing_user["_id"])
        role = existing_user.get("role", "buyer")
        await UserModel.update_last_login(email)

    access_token = create_access_token({
        "user_id": user_id,
        "email": email,
        "role": role,
    })

    refresh_token = create_refresh_token({
        "user_id": user_id,
        "email": email,
        "role": role,
    })

    return {
        "user": {
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "role": role,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/auth/url")
async def auth_url():
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    })
    return {
        "authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        "instructions": "Open the URL in a browser, login with Google, grab the ?code= from the redirect, then call GET /auth/google/callback?code=YOUR_CODE in Swagger",
    }
