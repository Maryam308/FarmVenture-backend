from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from .activity import ActivitySchema
from .user import UserResponseSchema

class BookingBase(BaseModel):
    """Base schema for booking data"""
    activity_id: int = Field(..., gt=0, description="ID of the activity to book")
    tickets_number: int = Field(default=1, ge=1, description="Number of tickets to book")  

class BookingCreate(BookingBase):
    """Schema for creating a new booking"""
    pass

class BookingUpdate(BaseModel):
    """Schema for updating a booking (all fields optional)"""
    tickets_number: Optional[int] = Field(None, ge=1, description="Number of tickets to book")  # REMOVED le=10
    status: Optional[str] = Field(None, description="Booking status: past, today, upcoming")

class BookingSchema(BaseModel):
    """Schema for returning booking data"""
    id: int  # CHANGED FROM booking_id TO id
    user_id: int
    activity_id: int
    tickets_number: int
    status: str
    booked_at: datetime
    
    # Include related data
    user: Optional[UserResponseSchema] = None
    activity: Optional[ActivitySchema] = None

    class Config:
        from_attributes = True

class BookingWithDetails(BookingSchema):
    """Schema with all details including user and activity"""
    user: UserResponseSchema
    activity: ActivitySchema

class BookingStats(BaseModel):
    """Schema for booking statistics"""
    total_bookings: int
    upcoming_bookings: int
    today_bookings: int
    past_bookings: int
    total_tickets: int