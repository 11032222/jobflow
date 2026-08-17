"""通用响应模型。"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageResult(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: list[T]
