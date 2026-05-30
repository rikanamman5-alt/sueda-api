import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from core.config import SECRET_KEY, ALGORITHM

security = HTTPBearer()


def get_current_user(token=Depends(security)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(required_roles: list):
    def role_checker(user=Depends(get_current_user)):
        if user.get("role") not in required_roles:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: insufficient permissions"
            )
        return user
    return role_checker
