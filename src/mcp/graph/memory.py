"""
Memory — short-term (conversation context) and long-term (knowledge).
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from src.mcp.graph.engine import State

logger = logging.getLogger('mcp_graph.memory')


class Memory(ABC):
    """Abstract memory store."""

    @abstractmethod
    async def save(self, state: Any) -> None:
        ...

    @abstractmethod
    async def load(self, conversation_id: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def clear(self, conversation_id: str) -> None:
        ...


@dataclass
class ShortTermMemory(Memory):
    """
    In-memory conversation buffer.
    Keeps recent conversation state in memory for fast access.
    """
    _store: Dict[str, Any] = field(default_factory=dict)

    async def save(self, state: Any) -> None:
        conv_id = state.conversation_id or state.graph_id
        self._store[conv_id] = state.copy()

    async def load(self, conversation_id: str) -> Optional[Any]:
        return self._store.get(conversation_id)

    async def clear(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)


@dataclass
class LongTermMemory(Memory):
    """
    File-based long-term memory.
    Stores conversation summaries and extracted knowledge.
    """
    base_dir: str = "data/memory"

    def __post_init__(self):
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, conv_id: str) -> str:
        safe = conv_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_dir, f"{safe}.json")

    async def save(self, state: Any) -> None:
        conv_id = state.conversation_id or state.graph_id
        path = self._path(conv_id)

        # Build a summary from messages
        summary = self._summarize(state.messages)

        existing = {}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        existing['conversation_id'] = conv_id
        existing['updated_at'] = time.time()
        existing['message_count'] = len(state.messages)
        existing['summary'] = summary
        existing['tool_results'] = list(state.tool_results.keys())
        existing['last_error'] = state.errors[-1] if state.errors else None

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2, default=str)

    async def load(self, conversation_id: str) -> Optional[Any]:
        path = self._path(conversation_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Return a lightweight state with memory metadata
        return State(
            conversation_id=conversation_id,
            metadata={k: v for k, v in data.items() if k != 'conversation_id'},
        )

    async def clear(self, conversation_id: str) -> None:
        path = self._path(conversation_id)
        if os.path.exists(path):
            os.remove(path)

    def _summarize(self, messages: List[Dict]) -> Dict[str, Any]:
        """Extract a concise summary from messages."""
        user_msgs = [m for m in messages if m.get('role') == 'user']
        tool_msgs = [m for m in messages if m.get('role') == 'tool']
        return {
            "total_messages": len(messages),
            "user_questions": len(user_msgs),
            "tool_calls": len(tool_msgs),
            "last_user_message": user_msgs[-1].get('content', '')[:200] if user_msgs else "",
        }
