from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .user import UserResponseSchema

class ActivityCreate(BaseModel):
    """Schema for creating a new activity"""
    title: str = Field(..., min_length=1, max_length=200, description="Title of the activity")
    description: str = Field(..., max_length=255, description="Description of the activity")
    date_time: datetime = Field(..., description="Date and time of the activity")
    duration_minutes: int = Field(default=60, gt=0, description="Duration in minutes")
    price: float = Field(..., ge=0, description="Price per person")
    max_capacity: int = Field(..., gt=0, description="Maximum number of participants")
    category: str = Field(..., max_length=50, description="Activity category")
    location: str = Field(..., max_length=200, description="Location of the activity")
    image_url: str = Field(..., max_length=500, description="URL of activity image")

class ActivityUpdate(BaseModel):
    """Schema for updating an activity (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=255)
    date_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, ge=0)
    max_capacity: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    category: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=200)
    image_url: Optional[str] = Field(None, max_length=500)

class ActivitySchema(BaseModel):
    """Schema for returning activity data"""
    id: int
    title: str
    description: str
    date_time: datetime
    duration_minutes: int
    price: float
    max_capacity: int
    current_capacity: int
    is_active: bool
    created_at: datetime
    user: UserResponseSchema
    category: str
    location: str
    image_url: str

    class Config:
        from_attributes = True