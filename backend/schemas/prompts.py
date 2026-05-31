"""Prompt template and history schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PromptTemplateCreate(BaseModel):
    title: str
    positive_prompt: str
    negative_prompt: str | None = None
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    scope: str = "project"  # global or project
    project_id: str | None = None


class PromptTemplateResponse(BaseModel):
    id: str
    title: str
    positive_prompt: str
    negative_prompt: str | None = None
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    scope: str
    project_id: str | None = None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptTemplateListResponse(BaseModel):
    items: list[PromptTemplateResponse]
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1


class PromptHistoryCreate(BaseModel):
    prompt_text: str
    negative_prompt: str | None = None
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    job_id: str | None = None
    project_id: str | None = None


class PromptHistoryResponse(BaseModel):
    id: str
    user_id: str
    project_id: str | None = None
    job_id: str | None = None
    prompt_text: str
    negative_prompt: str | None = None
    model_id: str | None = None
    lora_stack: list | None = None
    params: dict | None = None
    used_at: datetime

    model_config = {"from_attributes": True}


class PromptHistoryListResponse(BaseModel):
    items: list[PromptHistoryResponse]
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
