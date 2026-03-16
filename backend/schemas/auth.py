"""Auth schemas."""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str  # str instead of EmailStr to allow admin@localhost in dev
    password: str


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    global_role: str
    approval_state: str
    force_password_change: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo | None = None
    force_password_change: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    invite_token: str | None = None
