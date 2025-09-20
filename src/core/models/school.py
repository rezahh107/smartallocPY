"""School model representing the organisation a student belongs to."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class School(BaseModel):
    """Represents a school or educational centre."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    school_id: str = Field(..., alias="id", description="Unique identifier for the school")
    name: str = Field(..., min_length=1, description="Official name of the school")
    city: Optional[str] = Field(None, description="City in which the school operates")
    province: Optional[str] = Field(None, description="Province or region")
