"""Domain model representing a student."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Student(BaseModel):
    """Core representation of a student awaiting mentor allocation."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    student_id: str = Field(..., alias="id", description="Unique identifier for the student")
    first_name: str = Field(..., min_length=1, description="Student's first name")
    last_name: str = Field(..., min_length=1, description="Student's last name")
    grade_level: Optional[str] = Field(None, description="Current grade or academic level")
    mobile_number: Optional[str] = Field(
        None,
        description="Normalised mobile phone number including country code when available",
    )
    email: Optional[EmailStr] = Field(None, description="Primary email for the student")
    preferences: List[str] = Field(default_factory=list, description="Ordered mentor preferences")
    active: bool = Field(True, description="Flag used to disable allocation for the student")

    @field_validator("preferences", mode="before")
    @classmethod
    def _ensure_preferences_list(cls, value: Optional[List[str]]) -> List[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @property
    def full_name(self) -> str:
        """Return a display friendly version of the student's name."""

        return f"{self.first_name} {self.last_name}".strip()

    def is_assignable(self) -> bool:
        """Check if the student can participate in allocation."""

        return self.active
