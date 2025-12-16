from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import BaseModel

class HootModel(BaseModel):
    __tablename__ = "hoots"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)  # Text allows longer content than String
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign key linking to users table
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Relationships - these let us access related data easily!
    user = relationship('UserModel', back_populates='hoots')
    comments = relationship('CommentModel', back_populates='hoot', cascade='all, delete-orphan')