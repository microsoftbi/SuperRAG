# backend/app/schemas/user.py
import datetime

from pydantic import BaseModel, field_validator


class UserRegister(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 50:
            raise ValueError("用户名长度需在 2-50 字符之间")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    user: UserResponse