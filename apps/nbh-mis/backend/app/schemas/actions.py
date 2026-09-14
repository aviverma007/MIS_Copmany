from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ActionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    owner: str = Field(..., min_length=1, max_length=120)
    target_date: str  # ISO yyyy-mm-dd
    status: Optional[str] = "Open"


class ActionUpdate(BaseModel):
    title: Optional[str] = None
    owner: Optional[str] = None
    target_date: Optional[str] = None
    status: Optional[str] = None
