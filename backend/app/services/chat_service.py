from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import logging
import asyncio

from app.models.user import User
from app.models.message import Message
from app.services.llm import get_llm_provider, LLMProvider
from app.services.memory_service import MemoryService
from app.services.protocol_service import ProtocolService
from app.services.redis_service import RedisService
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Constants
MAX_CONTENT_LENGTH = 4000
LLM_TIMEOUT_SECONDS = 60
MAX_RETRIES = 2


class ChatServiceError(Exception):
    """Base exception for chat service errors."""
    pass


class LLMError(ChatServiceError):
    """Error from LLM provider."""
    pass


class ChatService:
    """
    Main chat service orchestrating message processing.
    Handles context building, LLM calls, and message persistence.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm: LLMProvider = get_llm_provider()
        self.memory_service = MemoryService(db)
        self.protocol_service = ProtocolService(db)
    
    async def get_history(
        self,
        user_id: UUID,
        cursor: Optional[datetime],
        limit: int
    ) -> Tuple[List[Message], bool, Optional[datetime]]:
        """
        Get chat history with cursor-based pagination.
        
        Args:
            user_id: User ID
            cursor: Timestamp cursor (messages older than this)
            limit: Number of messages to fetch (already validated by route)
            
        Returns:
            Tuple of (messages, has_more, next_cursor)
        """
        # Ensure limit is within bounds (defense in depth)
        limit = max(1, min(limit, 50))
        
        query = select(Message).where(Message.user_id == user_id)
        
        if cursor:
            query = query.where(Message.created_at < cursor)
        
        # Fetch one extra to check if there are more
        query = query.order_by(Message.created_at.desc()).limit(limit + 1)
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        next_cursor = messages[-1].created_at if messages and has_more else None
        
        # Reverse to chronological order for display
        messages.reverse()
        
        return messages, has_more, next_cursor
    
    async def process_message(
        self,
        user_id: UUID,
        content: str
    ) -> Tuple[Message, Message]:
        """
        Process a user message and generate AI response.
        
        Args:
            user_id: User ID
            content: Message content (already validated by schema)
            
        Returns:
            Tuple of (user_message, assistant_message)
            
        Raises:
            ValueError: If content is invalid
            LLMError: If LLM call fails
        """
        # Defense in depth: validate content even though schema should have done it
        if not content or not isinstance(content, str):
            raise ValueError("Message content is required")
        
        content = content.strip()
        if not content:
            raise ValueError("Message content cannot be empty")
        
        if len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(f"Message exceeds maximum length of {MAX_CONTENT_LENGTH} characters")
        
        redis = await RedisService.get_instance()
        
        # Set typing indicator
        await redis.set_typing(user_id, True)
        
        try:
            # Save user message first
            user_message = Message(
                user_id=user_id,
                role="user",
                content=content
            )
            self.db.add(user_message)
            await self.db.flush()
            
            # Build context for LLM
            context = await self._build_context(user_id, content)
            
            # Generate response with retry logic
            response_content = await self._generate_response_with_retry(context)
            
            # Validate response
            if not response_content or not response_content.strip():
                response_content = "I apologize, but I couldn't generate a response. Could you please try again?"
            
            # Truncate if response is too long (shouldn't happen, but safety check)
            if len(response_content) > 10000:
                response_content = response_content[:10000] + "..."
            
            # Save assistant message
            assistant_message = Message(
                user_id=user_id,
                role="assistant",
                content=response_content
            )
            self.db.add(assistant_message)
            await self.db.commit()
            
            return user_message, assistant_message
            
        except asyncio.TimeoutError:
            await self.db.rollback()
            logger.error("LLM request timed out")
            raise LLMError("Request timed out. Please try again.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise
        finally:
            await redis.set_typing(user_id, False)
    
    async def _generate_response_with_retry(
        self, 
        context: Dict[str, Any],
        max_retries: int = MAX_RETRIES
    ) -> str:
        """Generate LLM response with retry logic."""
        messages = self._build_llm_messages(context)
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self.llm.generate_response(
                        messages=messages,
                        max_tokens=settings.MAX_RESPONSE_TOKENS,
                        temperature=0.7
                    ),
                    timeout=LLM_TIMEOUT_SECONDS
                )
                return response
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                logger.warning(f"LLM timeout on attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries:
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        raise LLMError(f"Failed to generate response after {max_retries + 1} attempts: {last_error}")
    
    async def _build_context(self, user_id: UUID, current_message: str) -> Dict[str, Any]:
        """
        Build comprehensive context for LLM including:
        - User profile
        - Relevant protocols
        - Long-term memories
        - Recent chat history (within token budget)
        """
        # Get user (with error handling)
        try:
            user = await self.db.get(User, user_id)
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            user = None
        
        # Get relevant protocols (with error handling)
        try:
            protocols = await self.protocol_service.find_relevant_protocols(current_message)
        except Exception as e:
            logger.error(f"Error fetching protocols: {e}")
            protocols = []
        
        # Get relevant memories (with error handling)
        try:
            memories = await self.memory_service.get_relevant_memories(user_id, current_message)
        except Exception as e:
            logger.error(f"Error fetching memories: {e}")
            memories = []
        
        # Calculate token budget for chat history
        # Reserve tokens for: system prompt (~500), protocols (~500), memories (~200), response
        reserved_tokens = 1500 + settings.MAX_RESPONSE_TOKENS
        history_budget = settings.MAX_CONTEXT_TOKENS - reserved_tokens
        
        # Get recent messages within token budget
        try:
            recent_messages = await self._get_recent_messages_with_budget(
                user_id,
                max_tokens=max(1000, history_budget)  # Minimum 1000 tokens for history
            )
        except Exception as e:
            logger.error(f"Error fetching recent messages: {e}")
            recent_messages = []
        
        return {
            "user_profile": user.profile_data if user else {},
            "onboarding_completed": user.onboarding_completed if user else False,
            "protocols": protocols,
            "memories": memories,
            "recent_messages": recent_messages,
            "current_message": current_message
        }
    
    async def _get_recent_messages_with_budget(
        self,
        user_id: UUID,
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """
        Get recent messages while staying within token budget.
        Handles context overflow by truncating older messages.
        """
        # Ensure positive token budget
        max_tokens = max(100, max_tokens)
        
        # Fetch recent messages
        query = (
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(100)  # Reasonable upper bound
        )
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        # Select messages within token budget
        selected_messages = []
        token_count = 0
        
        for msg in messages:
            # Truncate individual messages if too long
            content = msg.content
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"
            
            msg_tokens = self.llm.count_tokens(content) + 10  # +10 for role overhead
            if token_count + msg_tokens > max_tokens:
                break
            selected_messages.append({
                "role": msg.role,
                "content": content
            })
            token_count += msg_tokens
        
        # Reverse to chronological order
        selected_messages.reverse()
        return selected_messages
    
    def _build_llm_messages(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build the messages array for LLM API call."""
        system_prompt = self._build_system_prompt(context)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in context.get("recent_messages", []):
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": context["current_message"]
        })
        
        return messages
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build comprehensive system prompt."""
        base_prompt = """You are a friendly, empathetic AI health coach having a WhatsApp-style conversation.

PERSONALITY:
- Warm, supportive, and conversational (like texting a knowledgeable friend)
- Use casual language, occasional emojis, and short paragraphs
- Be encouraging but never dismissive of concerns
- Ask follow-up questions to understand better

IMPORTANT GUIDELINES:
- Never diagnose conditions - suggest consulting healthcare providers for serious concerns
- For emergencies (chest pain, difficulty breathing, severe symptoms), immediately recommend calling emergency services
- Be supportive of mental health - suggest professional help when appropriate
- Remember and reference details the user has shared
- Keep responses concise (under 300 words unless detailed explanation needed)"""

        # Add protocols if relevant (limit to avoid context overflow)
        protocols = context.get("protocols", [])
        if protocols:
            base_prompt += "\n\n📋 RELEVANT PROTOCOLS TO FOLLOW:"
            for protocol in protocols[:3]:  # Limit to top 3 protocols
                content = protocol.get('content', '')
                # Truncate long protocol content
                if len(content) > 500:
                    content = content[:500] + "..."
                base_prompt += f"\n\n--- {protocol.get('name', 'Protocol')} ---\n{content}"
        
        # Add memories (limit to avoid context overflow)
        memories = context.get("memories", [])
        if memories:
            base_prompt += "\n\n🧠 WHAT YOU KNOW ABOUT THIS USER:"
            for memory in memories[:5]:  # Limit to top 5 memories
                content = memory.get('content', '')
                if len(content) > 100:
                    content = content[:100] + "..."
                base_prompt += f"\n- {content}"
        
        # Add user profile info
        profile = context.get("user_profile", {})
        if profile.get("name"):
            base_prompt += f"\n\nUser's name: {profile['name']}"
        
        # Onboarding context
        if not context.get("onboarding_completed"):
            base_prompt += """

🆕 ONBOARDING MODE:
This user is new. Gently gather information through natural conversation:
- Their name
- Health goals they're working towards
- Any existing conditions or concerns
- Lifestyle factors (exercise, diet, sleep patterns)

Do this conversationally, not as a checklist. Make them feel welcome!"""

        return base_prompt
    
    async def get_typing_status(self, user_id: UUID) -> Tuple[bool, Optional[datetime]]:
        """Get typing indicator status from Redis."""
        try:
            redis = await RedisService.get_instance()
            return await redis.get_typing_status(user_id)
        except Exception as e:
            logger.error(f"Error getting typing status: {e}")
            return False, None
    
    async def initialize_session(self, user_id: UUID) -> Dict[str, Any]:
        """
        Initialize or resume a chat session.
        Creates user if not exists and sends onboarding message for new users.
        """
        try:
            user = await self.db.get(User, user_id)
        except Exception as e:
            logger.error(f"Error fetching user during init: {e}")
            user = None
        
        if not user:
            # Create new user
            user = User(id=user_id)
            self.db.add(user)
            
            # Create onboarding message
            greeting = self._get_onboarding_message()
            onboarding_msg = Message(
                user_id=user_id,
                role="assistant",
                content=greeting
            )
            self.db.add(onboarding_msg)
            await self.db.commit()
            
            return {
                "is_new_user": True,
                "onboarding_completed": False,
                "user_id": user_id,
                "greeting": greeting
            }
        
        return {
            "is_new_user": False,
            "onboarding_completed": user.onboarding_completed,
            "user_id": user_id,
            "greeting": None
        }
    
    def _get_onboarding_message(self) -> str:
        """Get the initial onboarding message for new users."""
        return """Hey there! 👋 Welcome!

I'm your personal health coach, here to help you with health questions, wellness tips, and general guidance.

Before we dive in, I'd love to get to know you a bit better! Could you tell me:
• Your name
• What health goals you're working towards
• Any health concerns I should know about

Feel free to share as much or as little as you're comfortable with. What would you like to start with? 😊"""
