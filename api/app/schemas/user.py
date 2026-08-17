"""用户模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    phone: str | None = None
    real_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    real_name: str | None = None
    avatar_url: str | None = None
