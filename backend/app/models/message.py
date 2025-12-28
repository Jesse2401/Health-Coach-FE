from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_ = Column("metadata", JSONB, default={}, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_messages_user_created', 'user_id', 'created_at'),
        Index('idx_messages_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Message {self.id} role={self.role}>"

