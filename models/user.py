from sqlalchemy import Column, Integer, String, Enum
from .base import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
import jwt
from config.environment import secret
from sqlalchemy.orm import relationship
import enum

# Define UserRole enum
class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserModel(BaseModel):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)  



    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)

    def generate_token(self):
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
            "iat": datetime.now(timezone.utc),
            "sub": str(self.id),
            "role": self.role.value 
        }

        token = jwt.encode(payload, secret, algorithm="HS256")

        return token

    def is_admin(self):
        return self.role == UserRole.ADMIN