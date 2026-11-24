"""Domain models and data structures for the Four-Resource Deadlock simulation."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class ProcessState(Enum):
    """Lifecycle states of a simulated process."""
    INITIALIZING = "INITIALIZING"
    HOLDING = "HOLDING"          # Holding at least one resource, not yet blocked
    WAITING = "WAITING"          # Blocked waiting for an unavailable resource
    EXECUTING = "EXECUTING"      # Acquired all needed resources, performing work
    COMPLETED = "COMPLETED"      # Successfully finished work and released all resources
    DEADLOCKED = "DEADLOCKED"    # Confirmed deadlocked in a circular wait


class EdgeType(Enum):
    """Edge types in a standard bipartite Resource Allocation Graph (RAG)."""
    REQUEST = "REQUEST"          # Process -> Resource (Process is waiting for Resource)
    ASSIGNMENT = "ASSIGNMENT"    # Resource -> Process (Resource is held by Process)


class Resource:
    """A single-unit non-shareable system resource managed via a threading Lock."""

    def __init__(self, resource_id: str, name: str, rank: int) -> None:
        self.id = resource_id
        self.name = name
        self.rank = rank
        self._lock = threading.Lock()
        self._owner: Optional[str] = None
        self._state_lock = threading.Lock()

    @property
    def current_owner(self) -> Optional[str]:
        with self._state_lock:
            return self._owner

    def acquire(self, process_id: str, blocking: bool = True, timeout: float = -1) -> bool:
        """Attempt to acquire the resource lock."""
        acquired = self._lock.acquire(blocking=blocking, timeout=timeout)
        if acquired:
            with self._state_lock:
                self._owner = process_id
        return acquired

    def release(self, process_id: str) -> None:
        """Release the resource lock if held by the calling process."""
        with self._state_lock:
            if self._owner != process_id:
                raise RuntimeError(
                    f"Process {process_id} cannot release resource {self.id} "
                    f"currently owned by {self._owner}"
                )
            self._owner = None
        self._lock.release()

    def __repr__(self) -> str:
        return f"Resource({self.id}: {self.name}, rank={self.rank}, owner={self.current_owner})"


@dataclass
class ProcessInfo:
    """State tracking information for a single simulated process."""
    id: str
    name: str
    state: ProcessState = ProcessState.INITIALIZING
    held_resources: List[str] = field(default_factory=list)
    waiting_for: Optional[str] = None
    start_time: float = 0.0
    finish_time: float = 0.0
    error_message: Optional[str] = None

    @property
    def elapsed_time(self) -> float:
        if self.finish_time > 0:
            return self.finish_time - self.start_time
        if self.start_time > 0:
            return time.time() - self.start_time
        return 0.0


class ResourceAllocationGraph:
    """Thread-safe bipartite Resource Allocation Graph (RAG).

    Vertices are divided into Process nodes (P) and Resource nodes (R).
    Directed edges:
        P_i -> R_j: Request edge (P_i is waiting for R_j)
        R_j -> P_i: Assignment edge (R_j is held by P_i)
    """

    def __init__(
        self,
        process_ids: Optional[List[str]] = None,
        resource_ids: Optional[List[str]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self.process_nodes: Set[str] = set(process_ids or [])
        self.resource_nodes: Set[str] = set(resource_ids or [])
        # Adjacency list: node -> set of target nodes
        self.adj: Dict[str, Set[str]] = {}
        for p in self.process_nodes:
            self.adj[p] = set()
        for r in self.resource_nodes:
            self.adj[r] = set()

    def add_process(self, process_id: str) -> None:
        with self._lock:
            self.process_nodes.add(process_id)
            if process_id not in self.adj:
                self.adj[process_id] = set()

    def add_resource(self, resource_id: str) -> None:
        with self._lock:
            self.resource_nodes.add(resource_id)
            if resource_id not in self.adj:
                self.adj[resource_id] = set()

    def add_request(self, process_id: str, resource_id: str) -> None:
        """Add request edge: P_i -> R_j (Process is waiting for Resource)."""
        with self._lock:
            self.add_process(process_id)
            self.add_resource(resource_id)
            self.adj[process_id].add(resource_id)

    def grant_resource(self, process_id: str, resource_id: str) -> None:
        """Convert request to assignment: removes P_i -> R_j, adds R_j -> P_i."""
        with self._lock:
            self.add_process(process_id)
            self.add_resource(resource_id)
            # Remove request edge if present
            self.adj[process_id].discard(resource_id)
            # Add assignment edge
            self.adj[resource_id].add(process_id)

    def release_resource(self, process_id: str, resource_id: str) -> None:
        """Remove assignment edge: R_j -> P_i (Resource released)."""
        with self._lock:
            if resource_id in self.adj:
                self.adj[resource_id].discard(process_id)

    def get_adjacency_copy(self) -> Dict[str, Set[str]]:
        """Return a deep thread-safe snapshot of the graph adjacency list."""
        with self._lock:
            return {node: set(neighbors) for node, neighbors in self.adj.items()}

    def get_edges(self) -> List[Tuple[str, str, EdgeType]]:
        """Return all active edges labeled by edge type."""
        edges: List[Tuple[str, str, EdgeType]] = []
        with self._lock:
            for node, neighbors in self.adj.items():
                for neighbor in neighbors:
                    if node in self.process_nodes:
                        edges.append((node, neighbor, EdgeType.REQUEST))
                    else:
                        edges.append((node, neighbor, EdgeType.ASSIGNMENT))
        return edges

    def clear(self) -> None:
        with self._lock:
            for node in self.adj:
                self.adj[node].clear()

