from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class EventStatus(str, Enum):
    OPEN = "open"
    FULL = "full"
    CLOSED = "closed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CreateEvent(BaseModel):
    name: str = Field(..., description="The name of the event")
    description: str = Field(..., description="A brief description of the event")
    date: datetime = Field(
        ...,
        description="The date and time of the event (in UTC timezone)"
    )
    location: str = Field(..., description="The location/venue of the event")
    organiser: str = Field(..., description="The name of the organiser of the event")
    status: EventStatus = Field(EventStatus.OPEN, description="The status of the event")

    @classmethod
    @field_validator("date")
    def validate_future_date(cls, v):
        if v < datetime.now(timezone.utc):
            raise ValueError("Event date must be in the future")
        return v

class UpdateEvent(CreateEvent):
    pass

class EventQuery(BaseModel):
    name: str = Field(..., description="The name of the event")
