from pydantic import BaseModel


class AuthResponse(BaseModel):
    user: dict
    token: dict


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "buyer"
    address: str = ""
    contact_number: str = ""
    license_number: str = ""
    vehicle_brand: str = ""
    vehicle_model: str = ""
    vehicle_plate: str = ""
    vehicle_color: str = ""
    business_permit: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str
