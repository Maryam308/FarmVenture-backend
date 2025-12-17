from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import BaseModel
import enum

class BookingStatus(str, enum.Enum):
    PAST = "past"
    TODAY = "today"
    UPCOMING = "upcoming"

class BookingModel(BaseModel):
    __tablename__ = "bookings"

    # RENAME booking_id to id
    id = Column(Integer, primary_key=True, index=True, autoincrement=True) 
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_id = Column(Integer, ForeignKey('activities.id', ondelete='CASCADE'), nullable=False)
    tickets_number = Column(Integer, nullable=False, default=1)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.UPCOMING)
    booked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship('UserModel')
    activity = relationship('ActivityModel')

    def update_status(self):
        """Update booking status based on activity date"""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        activity_date = self.activity.date_time
        
        # Handle both naive and aware datetimes
        if activity_date.tzinfo is None:
            # If naive, assume UTC
            activity_date_aware = activity_date.replace(tzinfo=timezone.utc)
        else:
            activity_date_aware = activity_date
        
        # Compare dates
        if activity_date_aware.date() < now.date():
            self.status = BookingStatus.PAST
        elif activity_date_aware.date() == now.date():
            self.status = BookingStatus.TODAY
        else:
            self.status = BookingStatus.UPCOMING