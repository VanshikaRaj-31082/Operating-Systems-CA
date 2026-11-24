"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/generators/acyclic_pattern.py

Deterministic Workload Generator for Acyclic Resource Allocation Patterns.

Theoretical Characteristics:
1. Directed Acyclic Graph (DAG) Topology:
   - Dependency edges strictly flow in a topological direction (e.g., Pi -> Pj with i < j).
   - Circular wait condition is strictly absent (Cycles = []).
2. Process Cohorts:
   - Terminal Process (P_{n-1}): Holds resource allocations but has ZERO outstanding requests.
     Can always finish immediately, releasing its resources.
   - Dependent Processes (P_0 ... P_{n-2}): Can be configured as currently blocked on
     subsequent processes (Available = 0), creating a cascading release sequence without deadlock.
3. Multi-Instance Support:
   - Configurable total capacity per resource type.
4. Model Compliance:
   - Strictly validates all SystemState invariants and resource conservation laws.
"""

from __future__ import annotations

import random
from typing import List, Optional

from src.models import SystemState, InvariantViolation


class GeneratorError(Exception):
    """Raised when workload generator configuration parameters are invalid."""
    pass


def generate_acyclic_workload(
    n: int,
    m: int,
    total_per_type: int = 1,
    include_blocked: bool = True,
    seed: Optional[int] = None,
) -> SystemState:
    """
    Generates a deterministic acyclic resource allocation state guaranteed to be deadlock-free.

    Parameters
    ----------
    n : int
        Number of processes (must be >= 1).
    m : int
        Number of resource types (must be >= 1).
    total_per_type : int, default=1
        Total resource instances per type. Set to 1 for single-instance models.
    include_blocked : bool, default=True
        If True, creates a linear dependency chain where P_i requests resources held by P_{i+1},
        so processes are blocked until the terminal process P_{n-1} finishes.
        If False, processes have zero requests (uncontended safe state).
    seed : Optional[int], default=None
        Deterministic seed for reproducible generation.

    Returns
    -------
    SystemState
        Valid, immutable system state with acyclic dependency graph.

    Raises
    ------
    GeneratorError
        If dimensions or parameters are out of valid bounds.
    """
    if n < 1:
        raise GeneratorError(f"Process count n must be >= 1, got {n}")
    if m < 1:
        raise GeneratorError(f"Resource count m must be >= 1, got {m}")
    if total_per_type < 1:
        raise GeneratorError(f"total_per_type must be >= 1, got {total_per_type}")

    rng = random.Random(seed)

    total = [total_per_type] * m
    allocation = [[0] * m for _ in range(n)]
    request = [[0] * m for _ in range(n)]

    # Allocate resources: distribute available units along processes
    # Ensure every process holds at least one resource if n <= m
    for j in range(m):
        owner = j % n
        allocation[owner][j] = total[j]

    if include_blocked and n > 1:
        # Build acyclic dependency chain: P_i requests resource held by P_{i+1}
        # Terminal process P_{n-1} has zero requests, ensuring clean termination
        for i in range(n - 1):
            # Find a resource held by P_{i+1}
            held_by_next = [j for j in range(m) if allocation[i + 1][j] > 0]
            if held_by_next:
                # Pick deterministically via rng (or first)
                target_res = rng.choice(held_by_next)
                request[i][target_res] = 1

    return SystemState(
        total=total,
        allocation=allocation,
        request=request,
    )
