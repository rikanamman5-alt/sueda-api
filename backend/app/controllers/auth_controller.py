import json
import urllib.parse
import httpx
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from models.user_model import UserModel
from utils.jwt import create_access_token, create_refresh_token
from core.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from database.collections import users_collection
from bson.objectid import ObjectId

router = APIRouter(tags=["1. Auth"])

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login/google")
async def login_google():
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    })
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/auth/google")
async def auth_google(request: Request, code: str = None, error: str = None):
    if error:
        return HTMLResponse(content="<p>Google sign-in was denied. You may close this window.</p>")

    if not code:
        return HTMLResponse(content="<p>Missing authorization code. Authentication failed.</p>", status_code=400)

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_json = token_res.json()

        if not token_json.get("access_token"):
            return HTMLResponse(content="<p>Failed to exchange authorization code. Authentication failed.</p>", status_code=400)

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_json['access_token']}"},
        )
        if user_res.status_code != 200:
            return HTMLResponse(content="<p>Failed to get user info from Google.</p>", status_code=502)

        user_info = user_res.json()

    email = user_info["email"]

    existing_user = await users_collection.find_one({"email": email})

    if not existing_user:
        new_user = {
            "email": email,
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
            "provider": "google",
            "role": "buyer",
            "is_verified": True,
            "last_login": datetime.utcnow(),
        }
        result = await users_collection.insert_one(new_user)
        user_id = str(result.inserted_id)
        role = "buyer"
    else:
        user_id = str(existing_user["_id"])
        role = existing_user.get("role", "buyer")
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login": datetime.utcnow()}},
        )

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

    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": refresh_token}},
    )

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        safe_json = json.dumps({
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "role": role,
        }).replace("'", "\\'")
        html = f"""<!DOCTYPE html>
<html>
<head><title>Signing in...</title></head>
<body>
<script>
(function() {{
    var data = {{
        type: 'google-oauth',
        access_token: '{access_token}',
        refresh_token: '{refresh_token}',
        token_type: 'bearer',
        user: {safe_json}
    }};
    if (window.opener && !window.opener.closed) {{
        window.opener.postMessage(data, '*');
        window.close();
    }} else {{
        document.body.innerHTML = '<p>Signed in! You may close this window.</p>';
    }}
}})();
</script>
<p>Signing in...</p>
</body>
</html>"""
        return HTMLResponse(content=html)

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
