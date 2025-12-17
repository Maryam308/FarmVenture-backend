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

    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_id = Column(Integer, ForeignKey('activities.id', ondelete='CASCADE'), nullable=False)
    tickets_number = Column(Integer, nullable=False, default=1)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.UPCOMING)
    booked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships without back_populates
    user = relationship('UserModel')
    activity = relationship('ActivityModel')

    def update_status(self):
        """Update booking status based on activity date"""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        activity_date = self.activity.date_time
        
        if activity_date.date() < now.date():
            self.status = BookingStatus.PAST
        elif activity_date.date() == now.date():
            self.status = BookingStatus.TODAY
        else:
            self.status = BookingStatus.UPCOMING