from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import BaseModel

class CommentModel(BaseModel):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign keys
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    hoot_id = Column(Integer, ForeignKey('hoots.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    user = relationship('UserModel', back_populates='comments')
    hoot = relationship('HootModel', back_populates='comments')