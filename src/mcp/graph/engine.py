"""
LangGraph-inspired graph engine.

Core concepts:
  State     → plain dict[str, Any], no dataclass overhead
  Node      → async fn (state, ctx) → dict | Command
  Edge      → unconditional or conditional (fn(state) → str | None)
  Command   → {"goto": node_id | END, "update": dict}  (ala langgraph)
  END       → special sentinel stops execution
  Executor  → runs graph with streaming, interrupts, checkpointing
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, AsyncGenerator, Callable, Dict, List, Optional, Set, Tuple, Union,
)

from src.mcp.graph.checkpointer import Checkpointer, InMemoryCheckpointer, Checkpoint
from src.mcp.graph.memory import Memory, ShortTermMemory

logger = logging.getLogger('mcp_graph')

# ─── Constants ───────────────────────────────────────────────────────

END = "__end__"           # sentinel: stop execution
NodeId = str
RouterFn = Callable[['CommandContext'], Optional[str]]  # returns next node_id or None

class StreamMode(Enum):
    """Analogous to langgraph's stream_mode."""
    VALUES = "values"       # yield full state each step
    UPDATES = "updates"     # yield only the node's returned update dict


# ─── Command ─────────────────────────────────────────────────────────

@dataclass
class Command:
    """
    LangGraph-inspired control-flow primitive.

    - goto: next node to execute (default None = follow edges).
            Use END to stop.
    - update: state keys to merge before next node.
    """
    goto: Optional[str] = None
    update: Optional[Dict[str, Any]] = None

    @staticmethod
    def END() -> 'Command':
        return Command(goto="__end__")

    def to_dict(self) -> Dict:
        d: Dict = {}
        if self.goto:
            d["goto"] = self.goto
        if self.update:
            d["update"] = self.update
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Optional['Command']:
        if not d:
            return None
        return cls(goto=d.get("goto"), update=d.get("update"))


# ─── Execution Context ──────────────────────────────────────────────

@dataclass
class ExecutionContext:
    """Shared context — akin to langgraph's RunnableConfig."""
    graph_id: str = ""
    checkpointer: Optional[Checkpointer] = None
    memories: List[Memory] = field(default_factory=list)
    parent_ctx: Optional['ExecutionContext'] = None
    user_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    step: int = 0
    stream_mode: StreamMode = StreamMode.VALUES
    node: Optional[str] = None

    @property
    def root_ctx(self) -> 'ExecutionContext':
        ctx = self
        while ctx.parent_ctx:
            ctx = ctx.parent_ctx
        return ctx


# ─── Edge ───────────────────────────────────────────────────────────

@dataclass
class Edge:
    """A directed edge between two nodes."""
    source: str
    target: str
    condition: Optional[RouterFn] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ─── Graph ──────────────────────────────────────────────────────────

NodeFn = Callable[[Dict[str, Any], ExecutionContext], Any]
"""A node function: receives (state_dict, ctx), returns a dict (state update)
   or a Command. If it returns None, no update is applied."""


class Graph:
    """A directed graph of named node functions connected by edges."""

    def __init__(self, id: str = "graph"):
        self.id = id
        self.nodes: Dict[str, NodeFn] = {}
        self.edges: List[Edge] = []
        self.entry_point: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def add_node(self, name: str, fn: NodeFn) -> 'Graph':
        self.nodes[name] = fn
        if self.entry_point is None:
            self.entry_point = name
        return self

    def set_entry_point(self, name: str) -> 'Graph':
        self.entry_point = name
        return self

    def add_edge(self, source: str, target: str, condition: Optional[RouterFn] = None) -> 'Graph':
        self.edges.append(Edge(source=source, target=target, condition=condition))
        return self

    def get_next(self, current: str, ctx: 'CommandContext') -> Optional[str]:
        """Evaluate edges from `current`; return the first matching target or None."""
        for edge in self.edges:
            if edge.source != current:
                continue
            if edge.condition:
                target = edge.condition(ctx)
                if target and target == edge.target:
                    return target
            else:
                return edge.target
        return None

    def validate(self) -> List[str]:
        errs = []
        if not self.entry_point:
            errs.append("No entry_point set")
        elif self.entry_point not in self.nodes:
            errs.append(f"entry_point '{self.entry_point}' not in nodes")
        for e in self.edges:
            if e.source not in self.nodes:
                errs.append(f"edge source '{e.source}' not in nodes")
            if e.target not in self.nodes and e.target != END:
                errs.append(f"edge target '{e.target}' not in nodes/END")
        return errs


# ─── CommandContext (passed to router fns) ─────────────────────────

@dataclass
class CommandContext:
    """Minimal context for router conditions — just what they need."""
    state: Dict[str, Any]
    step: int
    current_node: str
    prev_node: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)


# ─── Executor ──────────────────────────────────────────────────────

class Executor:
    """
    Runs a Graph with streaming, interrupt, and checkpoint support.
    Analogous to langgraph's `.invoke()` / `.stream()`.
    """

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
        initial_state: Optional[Dict[str, Any]] = None,
        ctx: Optional[ExecutionContext] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """Run to completion. Returns (final_state, checkpoint_id)."""
        final = None
        cid = ""
        async for s, c in self._execute(initial_state or {}, ctx or ExecutionContext(graph_id=self.graph.id)):
            final = s
            cid = c
        return final, cid

    async def stream(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        ctx: Optional[ExecutionContext] = None,
    ) -> AsyncGenerator[Tuple[Dict[str, Any], str], None]:
        """Stream state after each node execution."""
        async for s, c in self._execute(initial_state or {}, ctx or ExecutionContext(graph_id=self.graph.id)):
            yield s, c

    async def _execute(
        self,
        state: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> AsyncGenerator[Tuple[Dict[str, Any], str], None]:
        errs = self.graph.validate()
        if errs:
            raise ValueError(f"Graph validation: {'; '.join(errs)}")

        state.setdefault("messages", [])
        state.setdefault("tool_results", {})
        state.setdefault("errors", [])
        state.setdefault("metadata", {})
        state.setdefault("interrupted", False)
        state.setdefault("interrupt_reason", None)
        state["graph_id"] = self.graph.id
        state["step"] = 0
        state["current_node"] = None

        current = self.graph.entry_point
        max_steps = 100

        while current and current != END and state.get("step", 0) < max_steps:
            # Interrupt check
            if state.get("interrupted"):
                cid = await self._checkpoint(state, ctx)
                yield state, cid
                break

            if current not in self.graph.nodes:
                state.setdefault("errors", []).append(f"Unknown node: '{current}'")
                break

            state["current_node"] = current
            node_fn = self.graph.nodes[current]
            ctx.node = current
            ctx.step = state.get("step", 0)

            # Pre-execution checkpoint
            cid = await self._checkpoint(state, ctx)
            yield state, cid

            logger.info(f"[{self.graph.id}] step={state['step']} node={current}")

            # Execute node
            try:
                result = await node_fn(state, ctx)
            except Exception as e:
                logger.exception(f"Node '{current}' failed")
                state.setdefault("errors", []).append(f"Node '{current}': {str(e)[:200]}")
                state["messages"].append({"role": "assistant", "content": f"❌ 执行出错：{str(e)[:200]}"})
                # On error, try to continue to next node or stop
                result = None

            # Process result: Command or dict update
            if isinstance(result, Command):
                if result.update:
                    state.update(result.update)
                if result.goto == END:
                    break
                if result.goto:
                    current = result.goto
                    state["step"] = state.get("step", 0) + 1
                    continue
            elif isinstance(result, dict):
                state.update(result)

            state["step"] = state.get("step", 0) + 1

            # Post-execution interrupt
            if state.get("interrupted"):
                cid = await self._checkpoint(state, ctx)
                yield state, cid
                break

            # Route to next node via edges
            cmd_ctx = CommandContext(
                state=state,
                step=state["step"],
                current_node=current,
                prev_node=state.get("current_node"),
            )
            next_id = self.graph.get_next(current, cmd_ctx)
            if next_id is None:
                logger.info(f"[{self.graph.id}] No outgoing edge from '{current}' — done")
                break
            current = next_id

        state["current_node"] = None
        cid = await self._checkpoint(state, ctx)

        # Save to memories
        for mem in ctx.memories:
            try:
                await mem.save(state)
            except Exception:
                pass

        yield state, cid

    async def _checkpoint(self, state: Dict[str, Any], ctx: ExecutionContext) -> str:
        if not self.checkpointer:
            return ""
        cp = Checkpoint(
            graph_id=self.graph.id,
            conversation_id=state.get("conversation_id", ""),
            state=state,
            timestamp=time.time(),
        )
        return await self.checkpointer.save(cp)

    async def interrupt(self, conv_id: str, reason: str = "User interrupted") -> bool:
        cp = await self.checkpointer.latest(conv_id)
        if not cp:
            return False
        cp.state["interrupted"] = True
        cp.state["interrupt_reason"] = reason
        await self.checkpointer.save(cp)
        return True

    async def resume(self, conv_id: str, user_input: str):
        cp = await self.checkpointer.latest(conv_id)
        if not cp:
            raise ValueError(f"No checkpoint for '{conv_id}'")
        state = cp.state
        state["interrupted"] = False
        state["interrupt_reason"] = None
        state["messages"].append({"role": "user", "content": user_input})
        ctx = ExecutionContext(
            graph_id=self.graph.id,
            checkpointer=self.checkpointer,
            memories=self.memories,
        )
        async for s, c in self._execute(state, ctx):
            yield s, c

    async def backtrack(self, conv_id: str, target_step: int) -> Optional[Dict]:
        for cp in reversed(await self.checkpointer.list(conv_id)):
            if cp.state.get("step", 0) <= target_step:
                return cp.state
        return None

    async def list_checkpoints(self, conv_id: str) -> List[Dict]:
        return [
            {
                "id": cp.id,
                "step": cp.state.get("step", 0),
                "current_node": cp.state.get("current_node"),
                "messages_count": len(cp.state.get("messages", [])),
                "interrupted": cp.state.get("interrupted", False),
                "timestamp": cp.timestamp,
            }
            for cp in await self.checkpointer.list(conv_id)
        ]
