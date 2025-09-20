"""Assignment model linking students and mentors."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AssignmentStatus(str, Enum):
    """Possible states for an assignment record."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Assignment(BaseModel):
    """Represents the allocation of a student to a mentor."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    assignment_id: str = Field(..., alias="id", description="Unique identifier for the assignment")
    student_id: str = Field(..., description="Identifier of the student")
    mentor_id: str = Field(..., description="Identifier of the mentor")
    status: AssignmentStatus = Field(AssignmentStatus.PENDING, description="Current assignment status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    notes: Optional[str] = Field(None, description="Optional note describing allocation context")
