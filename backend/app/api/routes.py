from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging
import time

from app.database import get_db
from app.schemas.chat import (
    SendMessageRequest,
    SendMessageResponse,
    ChatHistoryResponse,
    TypingStatusResponse,
    InitChatResponse,
    MessageResponse
)
from app.services.chat_service import ChatService
from app.services.memory_service import MemoryService
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Default user ID for single-session demo
# In production, this would come from authentication
DEFAULT_USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")

# Rate limiting: track last request time per user (in-memory for demo)
# In production, use Redis
_rate_limit_cache: dict[str, float] = {}
RATE_LIMIT_SECONDS = 1.0  # Minimum seconds between messages


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


def check_rate_limit(user_id: UUID) -> None:
    """
    Simple rate limiting to prevent spam.
    Raises RateLimitExceeded if too many requests.
    """
    key = str(user_id)
    now = time.time()
    
    if key in _rate_limit_cache:
        last_request = _rate_limit_cache[key]
        if now - last_request < RATE_LIMIT_SECONDS:
            raise RateLimitExceeded(
                f"Please wait {RATE_LIMIT_SECONDS} second(s) between messages"
            )
    
    _rate_limit_cache[key] = now


async def get_current_user_id() -> UUID:
    """
    Dependency to get current user ID.
    In production, this would extract user from JWT token.
    For this demo, we use a fixed user ID (single session).
    """
    return DEFAULT_USER_ID


@router.get("/init", response_model=InitChatResponse)
async def initialize_chat(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize chat session.
    
    - Creates user if not exists
    - Returns onboarding status
    - Returns initial greeting for new users
    
    Call this when the chat page loads.
    """
    try:
        chat_service = ChatService(db)
        result = await chat_service.initialize_session(user_id)
        return InitChatResponse(**result)
    except Exception as e:
        logger.error(f"Error initializing chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize chat session. Please refresh the page."
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    cursor: Optional[str] = Query(
        None,
        description="ISO timestamp cursor for pagination. Pass next_cursor from previous response to load older messages.",
        max_length=50  # Reasonable limit for timestamp string
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Number of messages to fetch (1-50)"
    ),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat history with cursor-based pagination.
    
    **Access Pattern**: Infinite scroll - load older messages on scroll up.
    
    - First call: No cursor, returns most recent messages
    - Subsequent calls: Pass `next_cursor` to load older messages
    - Messages are returned in chronological order (oldest first in batch)
    
    **Response**:
    - `messages`: Array of messages
    - `has_more`: Whether there are more older messages
    - `next_cursor`: Pass this to get the next batch of older messages
    """
    try:
        chat_service = ChatService(db)
        
        cursor_dt = None
        if cursor:
            # Validate cursor format
            cursor = cursor.strip()
            if not cursor:
                cursor_dt = None
            else:
                try:
                    # Handle various ISO formats
                    cursor_clean = cursor.replace('Z', '+00:00')
                    cursor_dt = datetime.fromisoformat(cursor_clean)
                    
                    # Sanity check: cursor shouldn't be in the future
                    if cursor_dt > datetime.now(cursor_dt.tzinfo) + timedelta(minutes=5):
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid cursor: timestamp is in the future"
                        )
                    
                    # Sanity check: cursor shouldn't be too old (e.g., before year 2020)
                    if cursor_dt.year < 2020:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid cursor: timestamp is too old"
                        )
                        
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid cursor format. Expected ISO timestamp (e.g., 2024-01-01T12:00:00Z)"
                    )
        
        messages, has_more, next_cursor = await chat_service.get_history(
            user_id=user_id,
            cursor=cursor_dt,
            limit=limit
        )
        
        return ChatHistoryResponse(
            messages=[MessageResponse.model_validate(m) for m in messages],
            has_more=has_more,
            next_cursor=next_cursor.isoformat() if next_cursor else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to load chat history. Please try again."
        )


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message and get AI response.
    
    **Flow**:
    1. Validates and saves user message
    2. Sets typing indicator (visible via /typing endpoint)
    3. Gathers context (recent messages + memories + protocols)
    4. Generates LLM response
    5. Extracts and saves any new memories (background)
    6. Returns both messages
    
    **Input Validation**:
    - Content must be 1-4000 characters
    - Empty/whitespace-only messages are rejected
    - Rate limited to 1 message per second
    
    **Response**:
    - `user_message`: The saved user message
    - `assistant_message`: The AI-generated response
    """
    # Rate limiting
    try:
        check_rate_limit(user_id)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    
    chat_service = ChatService(db)
    
    try:
        user_msg, assistant_msg = await chat_service.process_message(
            user_id=user_id,
            content=request.content
        )
        
        # Extract memories in background (non-blocking)
        # Create a new service instance for background task to avoid session issues
        background_tasks.add_task(
            _extract_memories_background,
            user_id,
            request.content,
            assistant_msg.content
        )
        
        return SendMessageResponse(
            user_message=MessageResponse.model_validate(user_msg),
            assistant_message=MessageResponse.model_validate(assistant_msg)
        )
        
    except ValueError as e:
        # Validation errors from service layer
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process message. Please try again."
        )


async def _extract_memories_background(
    user_id: UUID,
    user_message: str,
    assistant_response: str
):
    """Background task for memory extraction with its own DB session."""
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            memory_service = MemoryService(db)
            await memory_service.extract_and_save_memories(
                user_id,
                user_message,
                assistant_response
            )
    except Exception as e:
        # Log but don't fail - this is a background task
        logger.error(f"Background memory extraction failed: {e}", exc_info=True)


@router.get("/typing", response_model=TypingStatusResponse)
async def get_typing_status(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if AI is currently generating a response.
    
    **Usage**: Poll this endpoint to show typing indicator.
    Recommended polling interval: 1-2 seconds.
    
    **Response**:
    - `is_typing`: Whether the AI is currently generating
    - `started_at`: When typing started (for timeout handling)
    """
    try:
        chat_service = ChatService(db)
        is_typing, started_at = await chat_service.get_typing_status(user_id)
        
        return TypingStatusResponse(
            is_typing=is_typing,
            started_at=started_at
        )
    except Exception as e:
        logger.error(f"Error getting typing status: {e}", exc_info=True)
        # Return safe default instead of error
        return TypingStatusResponse(is_typing=False, started_at=None)
