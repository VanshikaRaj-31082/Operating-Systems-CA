"""Depth-First Search (DFS) Cycle Detection Engine for the Resource Allocation Graph."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from src.models import ResourceAllocationGraph


class CycleDetectionResult:
    """Encapsulates the outcome of cycle detection on the RAG."""

    def __init__(
        self,
        has_deadlock: bool,
        cycle_path: Optional[List[str]] = None,
        involved_processes: Optional[List[str]] = None,
        involved_resources: Optional[List[str]] = None,
    ) -> None:
        self.has_deadlock = has_deadlock
        self.cycle_path = cycle_path or []
        self.involved_processes = involved_processes or []
        self.involved_resources = involved_resources or []

    def format_cycle_path(self) -> str:
        """Return a human-readable arrow-formatted cycle string."""
        if not self.has_deadlock or not self.cycle_path:
            return "No cycle detected (Acyclic Graph - No Deadlock)"
        formatted_nodes = []
        for node in self.cycle_path:
            if node.startswith("P"):
                formatted_nodes.append(f"({node})")
            elif node.startswith("R"):
                formatted_nodes.append(f"[{node}]")
            else:
                formatted_nodes.append(node)
        return " -> ".join(formatted_nodes)

    def __repr__(self) -> str:
        if not self.has_deadlock:
            return "<CycleDetectionResult: No Deadlock>"
        return f"<CycleDetectionResult: Deadlock Cycle={self.format_cycle_path()}>"


class DeadlockDetector:
    """Detects cycles in a directed Resource Allocation Graph using 3-color DFS."""

    # Vertex states
    WHITE = 0  # Unvisited
    GRAY = 1   # On current recursion stack (ancestor)
    BLACK = 2  # Fully explored

    @classmethod
    def detect_cycle(cls, rag: ResourceAllocationGraph) -> CycleDetectionResult:
        """Inspect the current state of the RAG and determine whether a cycle exists."""
        adj = rag.get_adjacency_copy()
        all_nodes = sorted(list(adj.keys()))

        color: Dict[str, int] = {node: cls.WHITE for node in all_nodes}
        parent: Dict[str, Optional[str]] = {node: None for node in all_nodes}
        cycle_path: Optional[List[str]] = None

        def dfs(current: str, stack: List[str]) -> bool:
            nonlocal cycle_path
            color[current] = cls.GRAY
            stack.append(current)

            for neighbor in sorted(list(adj.get(current, set()))):
                if color[neighbor] == cls.GRAY:
                    # Back-edge detected! Reconstruct the cycle from the stack
                    idx = stack.index(neighbor)
                    cycle_path = stack[idx:] + [neighbor]
                    return True
                if color[neighbor] == cls.WHITE:
                    parent[neighbor] = current
                    if dfs(neighbor, stack):
                        return True

            stack.pop()
            color[current] = cls.BLACK
            return False

        for node in all_nodes:
            if color[node] == cls.WHITE:
                if dfs(node, []):
                    break

        if cycle_path is not None:
            procs = [n for n in cycle_path[:-1] if n.startswith("P")]
            res = [n for n in cycle_path[:-1] if n.startswith("R")]
            return CycleDetectionResult(
                has_deadlock=True,
                cycle_path=cycle_path,
                involved_processes=procs,
                involved_resources=res,
            )

        return CycleDetectionResult(has_deadlock=False)

