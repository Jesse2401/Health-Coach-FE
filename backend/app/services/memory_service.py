from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from typing import List, Dict
from uuid import UUID
import json
import logging

from app.models.memory import Memory
from app.services.llm import get_llm_provider

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for managing long-term user memories.
    Extracts important facts from conversations and retrieves relevant memories.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
    
    async def get_relevant_memories(
        self,
        user_id: UUID,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get memories relevant to the current query.
        Uses keyword matching for simplicity (no vector DB required).
        """
        # Get all user memories, ordered by importance and recency
        result = await self.db.execute(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.importance_score.desc(), Memory.last_accessed_at.desc())
            .limit(limit * 2)  # Fetch more, then filter
        )
        memories = result.scalars().all()
        
        if not memories:
            return []
        
        # Simple relevance: keyword overlap
        query_words = set(query.lower().split())
        scored_memories = []
        
        for memory in memories:
            memory_words = set(memory.content.lower().split())
            overlap = len(query_words & memory_words)
            score = overlap + memory.importance_score
            scored_memories.append((memory, score))
        
        # Sort by relevance score
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Update last_accessed_at for retrieved memories
        memory_ids = [m.id for m, _ in scored_memories[:limit]]
        if memory_ids:
            await self.db.execute(
                update(Memory)
                .where(Memory.id.in_(memory_ids))
                .values(last_accessed_at=func.now())
            )
        
        return [
            {
                "type": m.memory_type,
                "content": m.content,
                "importance": m.importance_score
            }
            for m, _ in scored_memories[:limit]
        ]
    
    async def extract_and_save_memories(
        self,
        user_id: UUID,
        user_message: str,
        assistant_response: str
    ) -> None:
        """
        Extract memorable information from conversation and save.
        Called as a background task after each exchange.
        """
        extraction_prompt = f"""Analyze this health coaching conversation and extract important facts about the user that should be remembered.

User said: "{user_message}"
Health coach responded: "{assistant_response}"

Extract facts in these categories ONLY if clearly stated:
- health_condition: Health conditions, symptoms, diagnoses, medications
- preference: Communication preferences, topics they like/dislike
- personal_info: Name, age, occupation, lifestyle factors
- goal: Health or wellness goals

Return a JSON object with a "memories" array. Each item should have:
- type: category from above
- content: the fact to remember (brief, factual)
- importance: 0.0-1.0 (how critical to remember)

Return {{"memories": []}} if nothing notable to extract.
Example: {{"memories": [{{"type": "health_condition", "content": "Has Type 2 diabetes", "importance": 0.9}}]}}"""

        try:
            response = await self.llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse JSON response
            # Handle potential markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            extracted = json.loads(response)
            memories = extracted.get("memories", [])
            
            for mem in memories:
                if mem.get("content") and mem.get("type"):
                    # Check for duplicate memories
                    existing = await self.db.execute(
                        select(Memory)
                        .where(Memory.user_id == user_id)
                        .where(Memory.content == mem["content"])
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    memory = Memory(
                        user_id=user_id,
                        memory_type=mem["type"],
                        content=mem["content"],
                        importance_score=min(1.0, max(0.0, mem.get("importance", 0.5)))
                    )
                    self.db.add(memory)
            
            await self.db.commit()
            logger.info(f"Extracted {len(memories)} memories for user {user_id}")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse memory extraction response: {e}")
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            # Don't raise - this is a background task

