from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Memory(Base):
    """
    Long-term memories extracted from conversations.
    Used to provide personalized context to the LLM.
    """
    __tablename__ = "memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_type = Column(String(50), nullable=False)  # 'health_condition', 'preference', 'personal_info', 'goal'
    content = Column(Text, nullable=False)
    importance_score = Column(Float, default=0.5, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    # Indexes
    __table_args__ = (
        Index('idx_memories_user', 'user_id'),
        Index('idx_memories_user_type', 'user_id', 'memory_type'),
    )
    
    def __repr__(self):
        return f"<Memory {self.id} type={self.memory_type}>"

