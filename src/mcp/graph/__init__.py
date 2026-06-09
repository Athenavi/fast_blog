"""
MCP Graph — LangGraph-style execution engine for AI agent workflows.

Architecture:
  Graph  ── composed of ──► Nodes + Edges
  State  ◄── checkpointed ──► Checkpointer (persistence)
  Executor ── runs ──► stream() / run() with interrupt/backtrack
  Memory  ── stores ──► short-term (conversation) + long-term (knowledge)
  Subgraph ── a Graph used as a Node in another Graph

Usage:
  from src.mcp.graph import Graph, AgentNode, ToolNode, RouterNode
"""

from src.mcp.graph.engine import (
    Graph, Node, Edge, State,
    Executor, ExecutionContext,
    RouterCondition,
)
from src.mcp.graph.checkpointer import (
    Checkpointer, Checkpoint,
    FileCheckpointer, InMemoryCheckpointer,
)
from src.mcp.graph.memory import (
    Memory, ShortTermMemory, LongTermMemory,
)
from src.mcp.graph.nodes import (
    InputNode, OutputNode,
    AgentNode, ToolNode, RouterNode,
    MCPToolNode,
)

__all__ = [
    'Graph', 'Node', 'Edge', 'State',
    'Executor', 'ExecutionContext',
    'RouterCondition',
    'Checkpointer', 'Checkpoint',
    'FileCheckpointer', 'InMemoryCheckpointer',
    'Memory', 'ShortTermMemory', 'LongTermMemory',
    'InputNode', 'OutputNode',
    'AgentNode', 'ToolNode', 'RouterNode',
    'MCPToolNode',
]
