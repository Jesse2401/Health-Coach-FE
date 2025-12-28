from typing import List, Dict
from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError, APITimeoutError
import logging

from app.services.llm.base import LLMProvider
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation of LLM provider."""
    
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=60.0,  # 60 second timeout
            max_retries=0  # We handle retries at service level
        )
        self.model = settings.LLM_MODEL if "claude" in settings.LLM_MODEL.lower() else "claude-3-sonnet-20240229"
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Generate response using Anthropic API.
        
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
        
        try:
            # Extract system message if present
            system_content = ""
            chat_messages = []
            
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                    
                role = msg.get("role", "").strip()
                content = msg.get("content", "").strip()
                
                if not content:
                    continue
                
                # Truncate very long messages
                if len(content) > 15000:
                    content = content[:15000] + "... [truncated]"
                
                if role == "system":
                    system_content = content
                elif role in ("user", "assistant"):
                    chat_messages.append({
                        "role": role,
                        "content": content
                    })
            
            # Claude requires messages to start with 'user' role
            # Remove leading assistant messages if any
            while chat_messages and chat_messages[0]["role"] != "user":
                chat_messages = chat_messages[1:]
            
            # Ensure alternating roles (Claude requirement)
            sanitized_messages = []
            last_role = None
            for msg in chat_messages:
                if msg["role"] == last_role:
                    # Merge consecutive same-role messages
                    if sanitized_messages:
                        sanitized_messages[-1]["content"] += "\n\n" + msg["content"]
                else:
                    sanitized_messages.append(msg)
                    last_role = msg["role"]
            
            if not sanitized_messages:
                raise ValueError("No valid messages to send")
            
            # Ensure last message is from user
            if sanitized_messages[-1]["role"] != "user":
                sanitized_messages.append({"role": "user", "content": "Please continue."})
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_content if system_content else None,
                messages=sanitized_messages,
                temperature=temperature
            )
            
            if not response.content:
                logger.warning("Anthropic returned empty content")
                return ""
            
            return response.content[0].text.strip()
            
        except RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {e}")
            raise RuntimeError("Service is temporarily busy. Please try again in a moment.")
        except APITimeoutError as e:
            logger.error(f"Anthropic timeout: {e}")
            raise RuntimeError("Request timed out. Please try again.")
        except APIConnectionError as e:
            logger.error(f"Anthropic connection error: {e}")
            raise RuntimeError("Unable to connect to AI service. Please check your connection.")
        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"AI service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected Anthropic error: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        Approximate token count for Claude.
        Claude uses ~4 characters per token on average.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
        
        # Handle very long text
        if len(text) > 100000:
            text = text[:100000]
        
        # Approximate: ~4 characters per token
        return max(1, len(text) // 4)
    
    def get_model_name(self) -> str:
        return self.model
