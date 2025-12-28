from typing import List, Dict
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
import tiktoken
import logging

from app.services.llm.base import LLMProvider
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation of LLM provider."""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=60.0,  # 60 second timeout
            max_retries=0  # We handle retries at service level
        )
        self.model = settings.LLM_MODEL if "gpt" in settings.LLM_MODEL.lower() else "gpt-4-turbo-preview"
        
        # Initialize tokenizer for token counting
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback for newer models
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Generate response using OpenAI API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response (capped at 4000)
            temperature: Sampling temperature (0-1, capped)
            
        Returns:
            Generated response text
            
        Raises:
            RuntimeError: If API call fails
        """
        # Validate and cap parameters
        max_tokens = max(100, min(max_tokens, 4000))
        temperature = max(0.0, min(temperature, 1.0))
        
        # Validate messages
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        # Sanitize messages
        sanitized_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "").strip()
            content = msg.get("content", "").strip()
            
            if role not in ("system", "user", "assistant"):
                continue
            if not content:
                continue
            
            # Truncate very long messages
            if len(content) > 15000:
                content = content[:15000] + "... [truncated]"
            
            sanitized_messages.append({"role": role, "content": content})
        
        if not sanitized_messages:
            raise ValueError("No valid messages to send")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=sanitized_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            content = response.choices[0].message.content
            if content is None:
                logger.warning("OpenAI returned None content")
                return ""
            
            return content.strip()
            
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise RuntimeError("Service is temporarily busy. Please try again in a moment.")
        except APITimeoutError as e:
            logger.error(f"OpenAI timeout: {e}")
            raise RuntimeError("Request timed out. Please try again.")
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise RuntimeError("Unable to connect to AI service. Please check your connection.")
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"AI service error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count (minimum 1)
        """
        if not text:
            return 0
        
        try:
            # Handle very long text by truncating for counting
            if len(text) > 100000:
                text = text[:100000]
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed, using estimate: {e}")
            # Fallback: estimate ~4 chars per token
            return max(1, len(text) // 4)
    
    def get_model_name(self) -> str:
        return self.model
