from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from models.base import BaseModel


class ProductModel(BaseModel):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)  
    price = Column(Float, nullable=False)
    category = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True) 
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationship 
    user = relationship('UserModel')
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"