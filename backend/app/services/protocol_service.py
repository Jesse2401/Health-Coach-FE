from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Set
import re

from app.models.protocol import Protocol


class ProtocolService:
    """
    Service for matching user queries against medical/policy protocols.
    Uses keyword matching to find relevant protocols.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_relevant_protocols(
        self,
        message: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Find protocols relevant to user's message using keyword matching.
        
        Args:
            message: User's message to match against
            limit: Maximum number of protocols to return
            
        Returns:
            List of relevant protocol dicts with name and content
        """
        # Extract words from message
        message_words = self._extract_keywords(message.lower())
        
        if not message_words:
            return []
        
        # Get all protocols
        result = await self.db.execute(
            select(Protocol).order_by(Protocol.priority.desc())
        )
        protocols = result.scalars().all()
        
        # Score protocols by keyword overlap
        scored_protocols = []
        for protocol in protocols:
            protocol_keywords = set(k.lower() for k in protocol.keywords)
            overlap = len(message_words & protocol_keywords)
            
            if overlap > 0:
                # Boost score by priority
                score = overlap * (1 + protocol.priority * 0.1)
                scored_protocols.append((protocol, score))
        
        # Sort by score descending
        scored_protocols.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "category": p.category,
                "content": p.content
            }
            for p, _ in scored_protocols[:limit]
        ]
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        # Remove punctuation and split into words
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter out common stop words
        stop_words = {
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it',
            'they', 'them', 'what', 'which', 'who', 'whom', 'this', 'that',
            'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall',
            'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as',
            'of', 'at', 'by', 'for', 'with', 'about', 'to', 'from', 'in',
            'on', 'up', 'out', 'off', 'over', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 'just', 'can', 'now', 'also', 'like', 'get', 'got',
            'really', 'feel', 'feeling', 'think', 'know', 'want', 'need'
        }
        
        return set(w for w in words if w not in stop_words and len(w) > 2)

