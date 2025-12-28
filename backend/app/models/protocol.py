from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid

from app.database import Base


class Protocol(Base):
    """
    Medical/policy protocols that guide the AI's responses.
    Matched against user queries using keywords.
    """
    __tablename__ = "protocols"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # 'medical', 'policy', 'general'
    keywords = Column(ARRAY(String), nullable=False, default=[])
    content = Column(Text, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_protocols_category', 'category'),
        Index('idx_protocols_keywords', 'keywords', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Protocol {self.name}>"

