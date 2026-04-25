import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    email: EmailStr = Field(..., examples=["usuario@ejemplo.com"])
    password: str = Field(..., examples=["MiPassword123"])

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password debe tener al menos una mayuscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password debe tener al menos una minuscula")
        if not re.search(r"\d", v):
            raise ValueError("Password debe tener al menos un numero")
        return v


class UserResponse(BaseModel):
    id: str = Field(..., examples=["662a1b2c3d4e5f6a7b8c9d0e"])
    email: EmailStr = Field(..., examples=["usuario@ejemplo.com"])
    is_confirmed: bool = Field(False, examples=[False])
    created_at: datetime = Field(..., examples=["2026-04-25T12:00:00Z"])

    model_config = {"from_attributes": True}


class UserInDB(BaseModel):
    email: EmailStr
    hashed_password: str
    is_confirmed: bool = False
    confirmation_token: Optional[str] = None
    created_at: Optional[datetime] = None

    def model_post_init(self, __context):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
