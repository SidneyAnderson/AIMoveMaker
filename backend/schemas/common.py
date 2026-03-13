"""Common Pydantic schemas shared across endpoints."""
from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    trace_id: str | None = None
