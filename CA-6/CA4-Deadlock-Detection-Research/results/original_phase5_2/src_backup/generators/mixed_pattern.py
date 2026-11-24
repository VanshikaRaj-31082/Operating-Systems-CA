"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/generators/mixed_pattern.py

Deterministic Workload Generator for Heterogeneous Mixed Allocation Scenarios.

Combines three distinct process cohorts within a single system:
1. Deadlocked Cohort: A circular wait cycle among k processes (P_0 ... P_{k-1}).
2. Blocked Cohort: Processes waiting on deadlocked resources, blocked behind the cycle
   without participating in any cycle (P_k ... P_{k+b-1}).
3. Safe Cohort: Independent processes holding resources with zero requests or satisfied
   requests, capable of terminating cleanly (P_{k+b} ... P_{n-1}).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from src.models import SystemState
from src.generators.acyclic_pattern import GeneratorError


@dataclass(frozen=True)
class MixedWorkloadSpec:
    """
    Metadata container documenting the ground-truth characteristics of a mixed workload.

    Attributes
    ----------
    state : SystemState
        The instantiated system state.
    deadlocked_cohort : List[int]
        Process indices belonging to the active deadlock cycle.
    blocked_cohort : List[int]
        Process indices transitively blocked behind the deadlock cycle.
    safe_cohort : List[int]
        Process indices that can complete safely and independently.
    cycle_size : int
        Size of the primary circular wait cycle.
    is_single_instance : bool
        Whether the resources are single-instance.
    """
    state: SystemState
    deadlocked_cohort: List[int]
    blocked_cohort: List[int]
    safe_cohort: List[int]
    cycle_size: int
    is_single_instance: bool


def generate_mixed_workload(
    n: int,
    m: int,
    deadlock_count: int = 2,
    blocked_count: int = 1,
    total_per_type: int = 1,
    seed: Optional[int] = None,
) -> MixedWorkloadSpec:
    """
    Generates a mixed workload combining safe, deadlocked, and blocked processes.

    Parameters
    ----------
    n : int
        Total process count (must be >= deadlock_count + blocked_count + 1).
    m : int
        Total resource types (must be >= deadlock_count + blocked_count + 1).
    deadlock_count : int, default=2
        Number of processes in the deadlock cycle (must be >= 2).
    blocked_count : int, default=1
        Number of processes blocked behind the deadlock cycle (must be >= 1).
    total_per_type : int, default=1
        Capacity per resource type (1 for single-instance, >1 for multi-instance).
    seed : Optional[int], default=None
        Deterministic seed for reproducible generation.

    Returns
    -------
    MixedWorkloadSpec
        Structured result containing the SystemState and ground-truth cohort classifications.

    Raises
    ------
    GeneratorError
        If process/resource counts or cohort partitions are invalid.
    """
    if deadlock_count < 2:
        raise GeneratorError(f"deadlock_count must be >= 2, got {deadlock_count}")
    if blocked_count < 1:
        raise GeneratorError(f"blocked_count must be >= 1, got {blocked_count}")

    min_required_processes = deadlock_count + blocked_count + 1
    if n < min_required_processes:
        raise GeneratorError(
            f"n ({n}) must be >= {min_required_processes} to fit deadlock, blocked, and safe cohorts"
        )

    min_required_resources = deadlock_count + blocked_count + 1
    if m < min_required_resources:
        raise GeneratorError(
            f"m ({m}) must be >= {min_required_resources} to fit distinct resource allocations"
        )

    rng = random.Random(seed)

    k = deadlock_count
    b = blocked_count
    s = n - k - b  # Safe cohort size (>= 1)

    deadlocked_cohort = list(range(0, k))
    blocked_cohort = list(range(k, k + b))
    safe_cohort = list(range(k + b, n))

    total = [total_per_type] * m
    allocation = [[0] * m for _ in range(n)]
    request = [[0] * m for _ in range(n)]

    # 1. Deadlocked Cohort: Circular wait cycle among P_0 ... P_{k-1}
    for i in range(k):
        res_held = i
        res_needed = (i + 1) % k
        allocation[i][res_held] = total[res_held]
        request[i][res_needed] = total[res_needed]

    # 2. Blocked Cohort: P_k ... P_{k+b-1} holds their own resource and waits on cycle (e.g. res 0)
    for idx, p in enumerate(blocked_cohort):
        res_held = k + idx
        allocation[p][res_held] = total[res_held]
        # Request a resource held by the deadlock cycle (e.g. R0 held by P0)
        target_cycle_res = rng.randint(0, k - 1)
        request[p][target_cycle_res] = 1

    # 3. Safe Cohort: P_{k+b} ... P_{n-1} holds their own resource and has ZERO requests
    for idx, p in enumerate(safe_cohort):
        res_held = (k + b + idx) % m
        # If resource is available, allocate
        allocated_so_far = sum(allocation[proc][res_held] for proc in range(n))
        remaining = total[res_held] - allocated_so_far
        if remaining > 0:
            allocation[p][res_held] = remaining
        # Safe processes have zero requests, allowing them to terminate immediately
        # and release their resources

    state = SystemState(
        total=total,
        allocation=allocation,
        request=request,
    )

    return MixedWorkloadSpec(
        state=state,
        deadlocked_cohort=deadlocked_cohort,
        blocked_cohort=blocked_cohort,
        safe_cohort=safe_cohort,
        cycle_size=k,
        is_single_instance=(total_per_type == 1),
    )
