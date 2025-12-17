from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import BaseModel

class ActivityModel(BaseModel):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False) 
    description = Column(String(255), nullable=False)  
    date_time = Column(DateTime, nullable=False)  
    duration_minutes = Column(Integer, default=60) 
    price = Column(Numeric(10, 2), nullable=False)
    max_capacity = Column(Integer, nullable=False)  
    current_capacity = Column(Integer, default=0) 
    is_active = Column(Boolean, default=True) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) 

    category = Column(String(50), nullable=False)  
    location = Column(String(200), nullable=False)  
    image_url = Column(String(500), nullable=False)  
    
    # Foreign key linking to users table
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    user = relationship('UserModel')
    
    @property
    def available_spots(self):
        """Calculate available spots dynamically"""
        return self.max_capacity - self.current_capacity