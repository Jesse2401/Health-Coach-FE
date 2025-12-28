from functools import lru_cache

from app.services.llm.base import LLMProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.anthropic_provider import AnthropicProvider
from app.config import get_settings

settings = get_settings()


@lru_cache()
def get_llm_provider() -> LLMProvider:
    """
    Factory function to get the configured LLM provider.
    Uses strategy pattern - provider is selected based on config.
    
    Returns:
        LLMProvider instance (OpenAI or Anthropic)
    """
    provider_name = settings.LLM_PROVIDER.lower()
    
    if provider_name == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        return OpenAIProvider()
    
    elif provider_name == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
        return AnthropicProvider()
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Use 'openai' or 'anthropic'")

