"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/generators/random_pattern.py

Deterministic Random Workload Generator for Statistical Monte Carlo Studies.

Theoretical Characteristics:
1. Strict Conservation by Construction:
   - Allocations are distributed from finite total pools, mathematically guaranteeing:
     sum_i(Allocation[i][j]) <= Total[j]  and  Available[j] >= 0.
2. Full Seed-Based Reproducibility:
   - Uses an isolated random.Random(seed) instance.
   - Identical (n, m, total, seed) inputs yield identical SystemState objects.
3. Parametric Allocation & Request Densities:
   - Configurable allocation ratios and request probabilities.
   - Accommodates single-instance (Total=1) and multi-instance (Total > 1) environments.
"""

from __future__ import annotations

import random
from typing import List, Optional

from src.models import SystemState
from src.generators.acyclic_pattern import GeneratorError


def generate_random_workload(
    n: int,
    m: int,
    total_instances: Optional[List[int]] = None,
    total_per_type: int = 1,
    allocation_ratio: float = 0.7,
    request_probability: float = 0.5,
    seed: Optional[int] = None,
) -> SystemState:
    """
    Generates a randomized, valid, invariant-preserving SystemState.

    Parameters
    ----------
    n : int
        Number of processes (must be >= 1).
    m : int
        Number of resource types (must be >= 1).
    total_instances : Optional[List[int]], default=None
        Explicit capacity vector. If None, uses total_per_type for all m types.
    total_per_type : int, default=1
        Total capacity per resource type if total_instances is None.
    allocation_ratio : float, default=0.7
        Target fraction of total resources to allocate across processes (0.0 to 1.0).
    request_probability : float, default=0.5
        Probability that a given process requests a given resource type (0.0 to 1.0).
    seed : Optional[int], default=None
        Deterministic seed for reproducible generation.

    Returns
    -------
    SystemState
        Valid, immutable system state satisfying all matrix invariants.

    Raises
    ------
    GeneratorError
        If dimensions, capacity, or probability parameters are invalid.
    """
    if n < 1:
        raise GeneratorError(f"Process count n must be >= 1, got {n}")
    if m < 1:
        raise GeneratorError(f"Resource count m must be >= 1, got {m}")
    if not (0.0 <= allocation_ratio <= 1.0):
        raise GeneratorError(f"allocation_ratio must be in [0.0, 1.0], got {allocation_ratio}")
    if not (0.0 <= request_probability <= 1.0):
        raise GeneratorError(f"request_probability must be in [0.0, 1.0], got {request_probability}")

    if total_instances is not None:
        if len(total_instances) != m:
            raise GeneratorError(
                f"total_instances length ({len(total_instances)}) must match m ({m})"
            )
        for j, tot in enumerate(total_instances):
            if tot < 1:
                raise GeneratorError(f"total_instances[{j}] must be >= 1, got {tot}")
        total = list(total_instances)
    else:
        if total_per_type < 1:
            raise GeneratorError(f"total_per_type must be >= 1, got {total_per_type}")
        total = [total_per_type] * m

    rng = random.Random(seed)

    allocation = [[0] * m for _ in range(n)]
    request = [[0] * m for _ in range(n)]

    # 1. Distribute allocations using a Binomial allocation model:
    # Each available unit has independent probability `allocation_ratio` of being allocated.
    # For cap=1 (single-instance), this is a Bernoulli trial: unit is allocated with probability allocation_ratio.
    # For cap=5, expected allocated units is 5 * allocation_ratio (e.g. 3.5 for ratio=0.7).
    for j in range(m):
        cap = total[j]
        units_to_allocate = 0
        if allocation_ratio >= 1.0:
            units_to_allocate = cap
        elif allocation_ratio > 0.0:
            # Sample from Binomial(cap, allocation_ratio) via independent Bernoulli trials
            for _ in range(cap):
                if rng.random() < allocation_ratio:
                    units_to_allocate += 1

        # Distribute the sampled units among processes
        for _ in range(units_to_allocate):
            p = rng.randint(0, n - 1)
            allocation[p][j] += 1

    # 2. Sample requests
    for i in range(n):
        for j in range(m):
            if rng.random() < request_probability:
                # Request a non-zero quantity up to the total capacity
                request[i][j] = rng.randint(1, total[j])
            else:
                request[i][j] = 0

    return SystemState(
        total=total,
        allocation=allocation,
        request=request,
    )
