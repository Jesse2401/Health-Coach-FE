from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re


# Constants for validation
MAX_MESSAGE_LENGTH = 4000
MIN_MESSAGE_LENGTH = 1


class SendMessageRequest(BaseModel):
    """Request schema for sending a message."""
    content: str = Field(
        ..., 
        min_length=MIN_MESSAGE_LENGTH, 
        max_length=MAX_MESSAGE_LENGTH,
        description="Message content (1-4000 characters)"
    )
    
    @field_validator('content', mode='before')
    @classmethod
    def preprocess_content(cls, v):
        """Pre-process content before validation."""
        if v is None:
            raise ValueError("Message content is required")
        if not isinstance(v, str):
            raise ValueError("Message content must be a string")
        return v
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize and validate message content."""
        # Strip leading/trailing whitespace
        v = v.strip()
        
        # Check for empty content after stripping
        if not v:
            raise ValueError("Message content cannot be empty or whitespace only")
        
        # Check length after stripping
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message content exceeds maximum length of {MAX_MESSAGE_LENGTH} characters")
        
        # Remove null bytes and other control characters (except newlines and tabs)
        v = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)
        
        # Normalize excessive whitespace (more than 3 consecutive newlines -> 2)
        v = re.sub(r'\n{4,}', '\n\n\n', v)
        
        # Limit consecutive spaces
        v = re.sub(r' {10,}', '    ', v)
        
        # Final check after sanitization
        if not v.strip():
            raise ValueError("Message content cannot be empty after sanitization")
        
        return v


class MessageResponse(BaseModel):
    """Response schema for a single message."""
    id: UUID
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history with pagination."""
    messages: List[MessageResponse]
    has_more: bool
    next_cursor: Optional[str] = None  # ISO timestamp for cursor-based pagination


class SendMessageResponse(BaseModel):
    """Response schema after sending a message."""
    user_message: MessageResponse
    assistant_message: MessageResponse


class TypingStatusResponse(BaseModel):
    """Response schema for typing indicator status."""
    is_typing: bool
    started_at: Optional[datetime] = None


class InitChatResponse(BaseModel):
    """Response schema for chat initialization."""
    is_new_user: bool
    onboarding_completed: bool
    user_id: UUID
    greeting: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    detail: str
    error_code: Optional[str] = None
