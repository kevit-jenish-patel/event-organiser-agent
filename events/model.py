from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EventStatus(str, Enum):
    OPEN = "open"
    FULL = "full"
    CLOSED = "closed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventBase(BaseModel):
    name: str = Field(..., description="The exact name of the event")
    description: str = Field(..., description="A brief description of the event")
    date: datetime = Field(
        ...,
        description="The date and time of the event strictly in ISO 8601 UTC format (e.g., '2026-04-15T15:00:00Z')"
    )
    location: str = Field(..., description="The location/venue of the event")
    organiser_id: int = Field(..., description="The id of the user organising the event")
    status: EventStatus = Field(EventStatus.OPEN, description="The status of the event")

    @field_validator("date")
    @classmethod
    def validate_future_date(cls, v: datetime) -> datetime:
        # Ensure timezone awareness before comparison
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < datetime.now(timezone.utc):
            raise ValueError("Event date must be in the future.")
        return v

# --- Internal Database Models ---

class EventDB(EventBase):
    """
    Internal model representing the exact document structure stored in MongoDB.
    This is NOT exposed to the LLM directly.
    """
    id: str = Field(..., alias="_id")
    createdAt: datetime
    updatedAt: Optional[datetime] = None
