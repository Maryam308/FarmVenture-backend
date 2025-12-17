from sqlalchemy import Column, Integer, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import BaseModel
import enum

class FavoriteType(str, enum.Enum):
    PRODUCT = "product"
    ACTIVITY = "activity"

class FavoriteModel(BaseModel):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    item_id = Column(Integer, nullable=False)  # ID of product or activity
    item_type = Column(String(20), nullable=False)  # 'product' or 'activity'
    
    # Relationships
    user = relationship('UserModel', backref='favorites')
    
    # Ensure a user can only favorite an item once
    __table_args__ = (
        UniqueConstraint('user_id', 'item_id', 'item_type', name='unique_user_item_favorite'),
    )
    
    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, item_id={self.item_id}, item_type={self.item_type})>"