"""Common Pydantic schemas shared across endpoints."""
import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    trace_id: str | None = None


class PaginatedResponse(BaseModel):
    """Standard paginated list envelope per PRD 13.11.

    All list endpoints MUST return this shape:
      { items: [...], total, page, page_size, pages }
    """
    items: list[Any]
    total: int
    page: int = 1
    page_size: int = 100
    pages: int = 1


def paginated(items: list, total: int, page: int = 1, page_size: int = 100) -> dict:
    """Build a standard paginated response dict."""
    pages = max(1, math.ceil(total / page_size)) if page_size > 0 else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
