"""
Core graph engine — nodes, edges, state, and executor with
interrupt/backtrack/stream support.
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, AsyncGenerator, Callable, Dict, List, Optional, Set, Tuple, Union,
)

from src.mcp.graph.checkpointer import Checkpointer, InMemoryCheckpointer, Checkpoint
from src.mcp.graph.memory import Memory, ShortTermMemory

logger = logging.getLogger('mcp_graph')


# ─── Types ───────────────────────────────────────────────────────────

NodeId = str
EdgeId = str
RouterCondition = Callable[['State'], str]  # returns next node_id


class NodeType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    AGENT = "agent"
    TOOL = "tool"
    ROUTER = "router"
    SUBGRAPH = "subgraph"


# ─── State ───────────────────────────────────────────────────────────

@dataclass
class State:
    """Serializable execution state — the 'whiteboard' passed between nodes."""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    current_node: Optional[str] = None
    step: int = 0
    graph_id: str = ""
    conversation_id: Optional[str] = None
    interrupted: bool = False
    interrupt_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "tool_results": self.tool_results,
            "metadata": self.metadata,
            "errors": self.errors,
            "current_node": self.current_node,
            "step": self.step,
            "graph_id": self.graph_id,
            "conversation_id": self.conversation_id,
            "interrupted": self.interrupted,
            "interrupt_reason": self.interrupt_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'State':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def copy(self) -> 'State':
        return State.from_dict(json.loads(json.dumps(self.to_dict(), default=str)))


# ─── Edge ────────────────────────────────────────────────────────────

@dataclass
class Edge:
    """Connects two nodes, optionally with a condition."""
    source: NodeId
    target: NodeId
    condition: Optional[RouterCondition] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ─── Node ────────────────────────────────────────────────────────────

class Node(ABC):
    """Base class for all graph nodes."""

    def __init__(
        self,
        id: NodeId,
        label: str = "",
        node_type: NodeType = NodeType.INPUT,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.label = label or id
        self.node_type = node_type
        self.config = config or {}

    @abstractmethod
    async def run(self, state: State, ctx: 'ExecutionContext') -> State:
        """Execute the node. Returns updated state."""
        ...

    async def stream(self, state: State, ctx: 'ExecutionContext') -> AsyncGenerator[State, None]:
        """Stream updates chunk by chunk. Default: yield final state."""
        result = await self.run(state, ctx)
        yield result


# ─── SubgraphNode ────────────────────────────────────────────────────

class SubgraphNode(Node):
    """A node that runs an entire sub-graph."""

    def __init__(self, id: str, graph: 'Graph', label: str = "", config: Optional[Dict] = None):
        super().__init__(id, label=label, node_type=NodeType.SUBGRAPH, config=config)
        self.subgraph = graph

    async def run(self, state: State, ctx: 'ExecutionContext') -> State:
        sub_ctx = ExecutionContext(
            graph=self.subgraph,
            checkpointer=ctx.checkpointer,
            memories=ctx.memories,
            parent_ctx=ctx,
        )
        executor = Executor(self.subgraph, checkpointer=ctx.checkpointer)
        final_state, _ = await executor.run(state, ctx=sub_ctx)
        return final_state

    async def stream(self, state: State, ctx: 'ExecutionContext') -> AsyncGenerator[State, None]:
        sub_ctx = ExecutionContext(
            graph=self.subgraph,
            checkpointer=ctx.checkpointer,
            memories=ctx.memories,
            parent_ctx=ctx,
        )
        executor = Executor(self.subgraph, checkpointer=ctx.checkpointer)
        async for s in executor.stream(state, ctx=sub_ctx):
            yield s


# ─── Graph ───────────────────────────────────────────────────────────

@dataclass
class Graph:
    """A directed graph of Nodes connected by Edges."""
    id: str
    nodes: Dict[NodeId, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    entry_point: Optional[NodeId] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node) -> 'Graph':
        self.nodes[node.id] = node
        if self.entry_point is None:
            self.entry_point = node.id
        return self

    def add_edge(self, source: NodeId, target: NodeId, condition: Optional[RouterCondition] = None) -> 'Graph':
        self.edges.append(Edge(source=source, target=target, condition=condition))
        return self

    def set_entry_point(self, node_id: NodeId) -> 'Graph':
        self.entry_point = node_id
        return self

    def get_next_nodes(self, current: NodeId, state: State) -> List[Tuple[NodeId, Edge]]:
        """Find all valid next nodes from current, evaluating conditions."""
        results = []
        for edge in self.edges:
            if edge.source != current:
                continue
            if edge.condition:
                target = edge.condition(state)
                if target and target == edge.target:
                    results.append((edge.target, edge))
            else:
                results.append((edge.target, edge))
        return results

    def validate(self) -> List[str]:
        errors = []
        if not self.entry_point:
            errors.append("No entry_point set")
        elif self.entry_point not in self.nodes:
            errors.append(f"entry_point '{self.entry_point}' not found in nodes")
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"Edge source '{edge.source}' not found in nodes")
            if edge.target not in self.nodes:
                errors.append(f"Edge target '{edge.target}' not found in nodes")
        return errors


# ─── Execution Context ──────────────────────────────────────────────

@dataclass
class ExecutionContext:
    """Shared context passed between nodes during execution."""
    graph: Graph
    checkpointer: Optional[Checkpointer] = None
    memories: List[Memory] = field(default_factory=list)
    parent_ctx: Optional['ExecutionContext'] = None
    user_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def root_ctx(self) -> 'ExecutionContext':
        ctx = self
        while ctx.parent_ctx:
            ctx = ctx.parent_ctx
        return ctx


# ─── Executor ───────────────────────────────────────────────────────

class Executor:
    """Runs a Graph with streaming, interrupt, and backtrack support."""

    def __init__(
        self,
        graph: Graph,
        checkpointer: Optional[Checkpointer] = None,
        memories: Optional[List[Memory]] = None,
    ):
        self.graph = graph
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        self.memories = memories or [ShortTermMemory()]

    async def run(
        self,
        initial_state: Optional[State] = None,
        ctx: Optional[ExecutionContext] = None,
    ) -> Tuple[State, str]:
        """Run the graph to completion. Returns (final_state, checkpoint_id)."""
        final_state = None
        checkpoint_id = ""
        async for state, cid in self._execute(initial_state or State(), ctx or ExecutionContext(graph=self.graph)):
            final_state = state
            checkpoint_id = cid
        return final_state, checkpoint_id

    async def stream(
        self,
        initial_state: Optional[State] = None,
        ctx: Optional[ExecutionContext] = None,
    ) -> AsyncGenerator[Tuple[State, str], None]:
        """Stream state updates through the graph."""
        async for state, cid in self._execute(initial_state or State(), ctx or ExecutionContext(graph=self.graph)):
            yield state, cid

    async def _execute(
        self,
        state: State,
        ctx: ExecutionContext,
    ) -> AsyncGenerator[Tuple[State, str], None]:
        errors = self.graph.validate()
        if errors:
            raise ValueError(f"Graph validation failed: {'; '.join(errors)}")

        state.graph_id = self.graph.id
        current_id = self.graph.entry_point
        visited: Set[str] = set()
        max_steps = 100

        while current_id and state.step < max_steps:
            # Check for interrupts
            if state.interrupted:
                state.current_node = current_id
                cid = await self._checkpoint(state, ctx)
                yield state, cid
                break

            node = self.graph.nodes.get(current_id)
            if not node:
                state.errors.append(f"Node '{current_id}' not found")
                break

            state.current_node = current_id
            visited.add(current_id)

            # Save pre-execution checkpoint
            cid = await self._checkpoint(state, ctx)
            yield state, cid

            logger.info(f"[Graph:{self.graph.id}] Running node: {node.id} ({node.label}) step={state.step}")

            # Run node with streaming
            async for chunk_state in node.stream(state, ctx):
                chunk_state.step = state.step
                cid = await self._checkpoint(chunk_state, ctx)
                yield chunk_state, cid

            state = chunk_state
            state.step += 1

            # Check for interrupt after node execution
            if state.interrupted:
                cid = await self._checkpoint(state, ctx)
                yield state, cid
                break

            # Find next node
            next_nodes = self.graph.get_next_nodes(current_id, state)
            if not next_nodes:
                logger.info(f"[Graph:{self.graph.id}] No outgoing edges from '{current_id}' — graph complete")
                break

            if len(next_nodes) > 1:
                logger.warning(f"[Graph:{self.graph.id}] Multiple next nodes from '{current_id}', taking first")
            current_id = next_nodes[0][0]

            # Loop detection
            if current_id in visited and len(visited) > 10:
                logger.warning(f"[Graph:{self.graph.id}] Possible loop detected at '{current_id}'")
                # Allow up to 3 visits per node
                if visited.count(current_id) >= 3:
                    state.errors.append(f"Loop detected: '{current_id}' visited {visited.count(current_id)} times")
                    break

        state.current_node = None
        cid = await self._checkpoint(state, ctx)

        # Save to memory
        for mem in ctx.memories:
            await mem.save(state)

        yield state, cid

    async def _checkpoint(self, state: State, ctx: ExecutionContext) -> str:
        if not self.checkpointer:
            return ""
        cp = Checkpoint(
            graph_id=self.graph.id,
            conversation_id=state.conversation_id or "",
            state=state.copy(),
            timestamp=time.time(),
        )
        return await self.checkpointer.save(cp)

    async def interrupt(self, conv_id: str, reason: str = "User requested interrupt") -> bool:
        """Interrupt a running conversation."""
        cp = await self.checkpointer.latest(conv_id)
        if not cp:
            return False
        cp.state.interrupted = True
        cp.state.interrupt_reason = reason
        await self.checkpointer.save(cp)
        return True

    async def resume(self, conv_id: str, user_input: str) -> AsyncGenerator[Tuple[State, str], None]:
        """Resume an interrupted conversation with new input."""
        cp = await self.checkpointer.latest(conv_id)
        if not cp:
            raise ValueError(f"No checkpoint for conversation '{conv_id}'")

        state = cp.state.copy()
        state.interrupted = False
        state.interrupt_reason = None

        # Add user message
        state.messages.append({"role": "user", "content": user_input})
        state.step = cp.state.step

        ctx = ExecutionContext(graph=self.graph, checkpointer=self.checkpointer, memories=self.memories)
        async for s, cid in self._execute(state, ctx):
            yield s, cid

    async def backtrack(self, conv_id: str, target_step: int) -> Optional[State]:
        """Backtrack to a specific step in conversation history."""
        checkpoints = await self.checkpointer.list(conv_id)
        # Find the checkpoint at or just before target_step
        for cp in reversed(checkpoints):
            if cp.state.step <= target_step:
                logger.info(f"[Backtrack] Restoring step {cp.state.step} for conv '{conv_id}'")
                return cp.state.copy()
        return None

    async def list_checkpoints(self, conv_id: str) -> List[Dict[str, Any]]:
        checkpoints = await self.checkpointer.list(conv_id)
        return [
            {
                "id": cp.id,
                "step": cp.state.step,
                "current_node": cp.state.current_node,
                "messages_count": len(cp.state.messages),
                "interrupted": cp.state.interrupted,
                "timestamp": cp.timestamp,
            }
            for cp in checkpoints
        ]
