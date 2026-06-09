"""
Checkpointer — persist and restore execution state.
Supports in-memory (default) and file-based storage.
"""

import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger('mcp_graph.checkpointer')


@dataclass
class Checkpoint:
    """A snapshot of execution state at a point in time."""
    graph_id: str
    conversation_id: str
    state: Any  # State object
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: Optional[str] = None  # For backtrack chains
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "graph_id": self.graph_id,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "state": self.state.to_dict() if hasattr(self.state, 'to_dict') else self.state,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], state_class=None) -> 'Checkpoint':
        from src.mcp.graph.engine import State as GraphState
        state_data = data.get("state", {})
        if state_class:
            state = state_class.from_dict(state_data) if hasattr(state_class, 'from_dict') else state_data
        else:
            state = GraphState.from_dict(state_data) if isinstance(state_data, dict) else state_data
        return cls(
            id=data.get("id", ""),
            parent_id=data.get("parent_id"),
            graph_id=data.get("graph_id", ""),
            conversation_id=data.get("conversation_id", ""),
            timestamp=data.get("timestamp", time.time()),
            state=state,
            metadata=data.get("metadata", {}),
        )


class Checkpointer(ABC):
    """Abstract base for checkpoint storage."""

    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> str:
        """Persist checkpoint. Returns its ID."""
        ...

    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a specific checkpoint by ID."""
        ...

    @abstractmethod
    async def latest(self, conversation_id: str) -> Optional[Checkpoint]:
        """Get the most recent checkpoint for a conversation."""
        ...

    @abstractmethod
    async def list(self, conversation_id: str) -> List[Checkpoint]:
        """List all checkpoints for a conversation (oldest first)."""
        ...

    @abstractmethod
    async def delete(self, conversation_id: str) -> None:
        """Delete all checkpoints for a conversation."""
        ...


class InMemoryCheckpointer(Checkpointer):
    """In-memory checkpoints (not persisted across restarts)."""

    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._conv_index: Dict[str, List[str]] = {}

    async def save(self, checkpoint: Checkpoint) -> str:
        self._checkpoints[checkpoint.id] = checkpoint
        conv = checkpoint.conversation_id
        if conv not in self._conv_index:
            self._conv_index[conv] = []
        self._conv_index[conv].append(checkpoint.id)
        return checkpoint.id

    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)

    async def latest(self, conversation_id: str) -> Optional[Checkpoint]:
        ids = self._conv_index.get(conversation_id, [])
        if not ids:
            return None
        return self._checkpoints.get(ids[-1])

    async def list(self, conversation_id: str) -> List[Checkpoint]:
        ids = self._conv_index.get(conversation_id, [])
        return [self._checkpoints[cid] for cid in ids if cid in self._checkpoints]

    async def delete(self, conversation_id: str) -> None:
        ids = self._conv_index.pop(conversation_id, [])
        for cid in ids:
            self._checkpoints.pop(cid, None)


class FileCheckpointer(Checkpointer):
    """File-based checkpoints (persisted to disk as JSON)."""

    def __init__(self, base_dir: str = "data/checkpoints"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _conv_path(self, conv_id: str) -> str:
        safe = conv_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_dir, safe)

    async def save(self, checkpoint: Checkpoint) -> str:
        path = self._conv_path(checkpoint.conversation_id)
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, f"{checkpoint.id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        return checkpoint.id

    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        import glob
        # Search across all conversation dirs
        for fpath in glob.glob(os.path.join(self.base_dir, "*", f"{checkpoint_id}.json")):
            with open(fpath, 'r', encoding='utf-8') as f:
                return Checkpoint.from_dict(json.load(f))
        return None

    async def latest(self, conversation_id: str) -> Optional[Checkpoint]:
        path = self._conv_path(conversation_id)
        if not os.path.isdir(path):
            return None
        files = sorted(
            [f for f in os.listdir(path) if f.endswith('.json')],
            key=lambda f: os.path.getmtime(os.path.join(path, f)),
        )
        if not files:
            return None
        with open(os.path.join(path, files[-1]), 'r', encoding='utf-8') as f:
            return Checkpoint.from_dict(json.load(f))

    async def list(self, conversation_id: str) -> List[Checkpoint]:
        path = self._conv_path(conversation_id)
        if not os.path.isdir(path):
            return []
        files = sorted([f for f in os.listdir(path) if f.endswith('.json')],
                       key=lambda f: os.path.getmtime(os.path.join(path, f)))
        result = []
        for fname in files:
            with open(os.path.join(path, fname), 'r', encoding='utf-8') as f:
                result.append(Checkpoint.from_dict(json.load(f)))
        return result

    async def delete(self, conversation_id: str) -> None:
        import shutil
        path = self._conv_path(conversation_id)
        if os.path.isdir(path):
            shutil.rmtree(path)
