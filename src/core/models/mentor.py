"""Domain model representing a mentor."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Mentor(BaseModel):
    """Representation of a mentor/teacher that can be matched with students."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    mentor_id: str = Field(..., alias="id", description="Unique identifier for the mentor")
    first_name: str = Field(..., description="Mentor's first name")
    last_name: str = Field(..., description="Mentor's last name")
    expertise_areas: List[str] = Field(default_factory=list, description="Subject focus areas")
    capacity: int = Field(5, ge=0, description="Maximum number of students the mentor can manage")
    active: bool = Field(True, description="Whether the mentor is available for allocation")

    @field_validator("expertise_areas", mode="before")
    @classmethod
    def _ensure_areas(cls, value: List[str]) -> List[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @property
    def full_name(self) -> str:
        """Return a display name for the mentor."""

        return f"{self.first_name} {self.last_name}".strip()

    def has_capacity(self, current_load: int) -> bool:
        """Check whether there is still space for additional students."""

        if not self.active:
            return False
        return current_load < self.capacity
