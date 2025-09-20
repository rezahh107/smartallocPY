"""Manager model representing supervisors of mentor centres."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class Manager(BaseModel):
    """Represents a manager responsible for a group of mentors or centres."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    manager_id: str = Field(..., alias="id", description="Unique identifier for the manager")
    name: str = Field(..., min_length=1, description="Manager's full name")
    center_codes: List[str] = Field(default_factory=list, description="Centres managed by the manager")
