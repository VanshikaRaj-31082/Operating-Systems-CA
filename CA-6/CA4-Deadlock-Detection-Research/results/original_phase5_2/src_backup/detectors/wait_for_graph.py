"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/detectors/wait_for_graph.py

Single-Instance Deadlock Detector using Wait-For Graph (WFG) Analysis.

Principles:
1. Graph Construction:
   - Vertices: Active processes {0, ..., n-1}.
   - Directed Edge Pi -> Pj: Process Pi is waiting for a resource currently held by Pj.
   - In a single-instance system, a cycle in the WFG is both a NECESSARY and SUFFICIENT
     condition for deadlock.
2. DFS Cycle Detection:
   - Uses Depth-First Search to detect all elementary directed cycles.
   - Cycle members are identified as the actual deadlocked processes.
3. Separation of Blocked Processes:
   - Processes blocked behind deadlocked processes (Pi -> P_deadlocked) are identified
     separately as `blocked_processes` and are NOT classified as members of the deadlock cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set
from collections import deque

from src.models import SystemState


@dataclass(frozen=True)
class WFGResult:
    """
    Structured immutable result of Wait-For Graph deadlock analysis.

    Attributes
    ----------
    is_deadlocked : bool
        True if at least one directed cycle was detected in the graph.
    deadlocked_processes : List[int]
        Sorted list of process indices that belong to at least one deadlock cycle.
    cycles : List[List[int]]
        List of detected elementary cycles, each formatted canonically.
    blocked_processes : List[int]
        Sorted list of process indices that can reach a deadlock cycle via directed
        wait edges, but are NOT themselves part of any cycle.
    adjacency_list : Dict[int, List[int]]
        Adjacency list representation of the directed Wait-For Graph.
    edge_count : int
        Total number of directed wait edges in the graph.
    is_single_instance : bool
        Whether the input system state has single-instance resources.
    """
    is_deadlocked: bool
    deadlocked_processes: List[int]
    cycles: List[List[int]]
    blocked_processes: List[int]
    adjacency_list: Dict[int, List[int]]
    edge_count: int
    is_single_instance: bool


def build_wait_for_graph(state: SystemState) -> Dict[int, List[int]]:
    """
    Constructs the directed Wait-For Graph adjacency list from a SystemState.

    Edge Condition:
    An edge Pi -> Pj is added if:
    - Pi has an unsatisfied request for resource k (Request[i][k] > Available[k]), AND
    - Pj holds an allocation of resource k (Allocation[j][k] > 0, with j != i).

    Parameters
    ----------
    state : SystemState
        The current system resource allocation state.

    Returns
    -------
    Dict[int, List[int]]
        Adjacency list mapping each process index to its list of dependent process indices.
    """
    n = state.n
    m = state.m
    allocation = state.allocation
    request = state.request
    available = state.available

    adj: Dict[int, List[int]] = {i: [] for i in range(n)}

    for i in range(n):
        for k in range(m):
            # Process i is waiting for resource k if its request cannot be satisfied from available
            if request[i][k] > available[k]:
                # Find all other processes j holding resource k
                for j in range(n):
                    if j != i and allocation[j][k] > 0:
                        if j not in adj[i]:
                            adj[i].append(j)

    # Ensure neighbor lists are sorted for deterministic behavior
    for i in range(n):
        adj[i].sort()

    return adj


def find_elementary_cycles(adj: Dict[int, List[int]], n: int) -> List[List[int]]:
    """
    Detects all elementary directed cycles in the graph using DFS.
    
    Each detected cycle is canonicalized to begin with its smallest node index
    and deduplicated.
    """
    cycles: List[List[int]] = []
    seen_cycles: Set[tuple] = set()

    for start_node in range(n):
        stack: List[int] = [start_node]
        in_stack: Set[int] = {start_node}

        def dfs(current: int):
            for neighbor in adj[current]:
                if neighbor == start_node:
                    # Found a cycle back to start_node
                    cycle = list(stack)
                    # Canonicalize: rotate so smallest index is first
                    min_idx = cycle.index(min(cycle))
                    canonical = tuple(cycle[min_idx:] + cycle[:min_idx])
                    if canonical not in seen_cycles:
                        seen_cycles.add(canonical)
                        cycles.append(list(canonical))
                elif neighbor > start_node and neighbor not in in_stack:
                    in_stack.add(neighbor)
                    stack.append(neighbor)
                    dfs(neighbor)
                    stack.pop()
                    in_stack.remove(neighbor)

        dfs(start_node)

    # Sort cycles deterministically
    cycles.sort(key=lambda c: (len(c), c))
    return cycles


def find_blocked_processes(
    adj: Dict[int, List[int]],
    n: int,
    deadlocked_set: Set[int]
) -> List[int]:
    """
    Identifies processes that can reach a deadlocked process via directed paths,
    but are NOT part of any cycle themselves.
    """
    if not deadlocked_set:
        return []

    blocked: List[int] = []

    for p in range(n):
        if p in deadlocked_set:
            continue

        # Check reachability to any deadlocked node via BFS
        visited: Set[int] = {p}
        queue = deque([p])
        can_reach_deadlock = False

        while queue:
            curr = queue.popleft()
            if curr in deadlocked_set:
                can_reach_deadlock = True
                break

            for neighbor in adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if can_reach_deadlock:
            blocked.append(p)

    blocked.sort()
    return blocked


def detect_wfg_deadlock(state: SystemState) -> WFGResult:
    """
    Performs Wait-For Graph deadlock detection on the given SystemState.

    Parameters
    ----------
    state : SystemState
        The resource allocation state to analyze.

    Returns
    -------
    WFGResult
        Structured detection results containing cycle status, deadlocked processes,
        detected cycles, blocked processes, and the graph adjacency list.
    """
    adj = build_wait_for_graph(state)
    edge_count = sum(len(neighbors) for neighbors in adj.values())
    cycles = find_elementary_cycles(adj, state.n)

    deadlocked_set: Set[int] = set()
    for cycle in cycles:
        deadlocked_set.update(cycle)

    deadlocked_processes = sorted(list(deadlocked_set))
    blocked_processes = find_blocked_processes(adj, state.n, deadlocked_set)
    is_deadlocked = len(deadlocked_processes) > 0

    return WFGResult(
        is_deadlocked=is_deadlocked,
        deadlocked_processes=deadlocked_processes,
        cycles=cycles,
        blocked_processes=blocked_processes,
        adjacency_list=adj,
        edge_count=edge_count,
        is_single_instance=state.is_single_instance,
    )
