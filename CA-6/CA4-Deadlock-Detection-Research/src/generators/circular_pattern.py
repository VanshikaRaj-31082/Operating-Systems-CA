"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/generators/circular_pattern.py

Deterministic Workload Generator for Circular Wait Resource Allocation Patterns.

Theoretical Characteristics:
1. Controlled Cycle Sizes:
   - Constructs a closed circular dependency chain of length k (2 <= k <= min(n, m)):
     P_0 -> P_1 -> ... -> P_{k-1} -> P_0
2. Single-Instance & Multi-Instance Compatibility:
   - Single-Instance: Total[j] = 1. Graph cycle is necessary and sufficient for deadlock.
   - Multi-Instance: Total[j] > 1. All instances of cycle resources are allocated to cycle
     members, ensuring Available capacity cannot break the deadlock.
3. Transitive Blocked Tails:
   - Configurable inclusion of non-cycle processes waiting on cycle members.
4. Mathematical Invariant Preservation:
   - Guaranteed resource conservation and non-negative matrix bounds.
"""

from __future__ import annotations

import random
from typing import List, Optional

from src.models import SystemState
from src.generators.acyclic_pattern import GeneratorError


def generate_circular_workload(
    n: int,
    m: int,
    cycle_size: Optional[int] = None,
    total_per_type: int = 1,
    include_blocked_tail: bool = False,
    seed: Optional[int] = None,
) -> SystemState:
    """
    Generates a deterministic system state with a verified circular wait deadlock.

    Parameters
    ----------
    n : int
        Number of processes (must be >= 2).
    m : int
        Number of resource types (must be >= 2).
    cycle_size : Optional[int], default=None
        Size of the circular wait cycle (2 <= cycle_size <= min(n, m)).
        If None, defaults to min(n, m).
    total_per_type : int, default=1
        Total resource instances per type. Set to 1 for single-instance models.
    include_blocked_tail : bool, default=False
        If True, processes outside the cycle (P_k ... P_{n-1}) request resources held
        by cycle members, placing them in a blocked-behind-deadlock state.
    seed : Optional[int], default=None
        Deterministic seed for reproducible generation.

    Returns
    -------
    SystemState
        Valid system state containing a confirmed circular wait.

    Raises
    ------
    GeneratorError
        If dimensions or cycle parameters are invalid.
    """
    if n < 2:
        raise GeneratorError(f"Process count n must be >= 2 for circular wait, got {n}")
    if m < 2:
        raise GeneratorError(f"Resource count m must be >= 2 for circular wait, got {m}")
    if total_per_type < 1:
        raise GeneratorError(f"total_per_type must be >= 1, got {total_per_type}")

    max_possible_cycle = min(n, m)
    if cycle_size is None:
        k = max_possible_cycle
    else:
        if cycle_size < 2 or cycle_size > max_possible_cycle:
            raise GeneratorError(
                f"cycle_size must be between 2 and min(n, m)={max_possible_cycle}, got {cycle_size}"
            )
        k = cycle_size

    rng = random.Random(seed)

    total = [total_per_type] * m
    allocation = [[0] * m for _ in range(n)]
    request = [[0] * m for _ in range(n)]

    # 1. Construct the core cycle among P_0 ... P_{k-1}
    for i in range(k):
        res_held = i
        res_needed = (i + 1) % k

        # Allocate all units of res_held to process i to ensure Available is 0
        allocation[i][res_held] = total[res_held]
        # Request at least 1 unit (or all units) of res_needed
        request[i][res_needed] = total[res_needed]

    # 2. Handle remaining resources (if m > k)
    for j in range(k, m):
        owner = j % n
        allocation[owner][j] = total[j]

    # 3. Handle processes outside the cycle (P_k ... P_{n-1})
    if n > k:
        for i in range(k, n):
            if include_blocked_tail:
                # Process i requests a resource held by a cycle member (e.g., resource 0)
                # It becomes blocked behind the deadlocked cycle
                target_cycle_res = rng.randint(0, k - 1)
                request[i][target_cycle_res] = 1
            else:
                # Safe / uncontentious: process i has zero requests and can finish
                pass

    return SystemState(
        total=total,
        allocation=allocation,
        request=request,
    )
