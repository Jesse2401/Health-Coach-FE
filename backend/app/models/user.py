from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    profile_data = Column(JSONB, default={}, nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="user", lazy="dynamic")
    memories = relationship("Memory", back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User {self.id}>"

