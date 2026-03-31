from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from pydantic.v1 import EmailStr


class UserBase(BaseModel):
    name: str = Field(..., description="Full name of the user")
    email: EmailStr = Field(..., description="Unique email address of the user")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")

class UserDB(UserBase):
    """
    Internal model representing the exact document structure stored in MongoDB.
    This is NOT exposed to the LLM directly.
    """
    id: str = Field(..., alias="_id")
    createdAt: datetime
    updatedAt: Optional[datetime] = None
