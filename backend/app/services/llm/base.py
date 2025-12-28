from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Implements the Strategy pattern for swappable LLM backends.
    """
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text for context window management.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Approximate token count
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name being used."""
        pass

