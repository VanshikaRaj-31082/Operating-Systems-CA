"""
CA2 - Deadlock Detection and Avoidance
Workload Generator: reproducible synthetic system-state generation
and systematic boundary sweeps.

This module generates SystemState objects and Request matrices for use
by bankers_algorithm.py (Phase 2) and deadlock_detector.py (Phase 3)
experiments.  All generated data satisfies every invariant enforced
by SystemState:

    1. Non-negativity of all entries.
    2. Total[j] > 0 for every resource type j.
    3. Allocation[i][j] <= Max[i][j] for all i, j.
    4. Need = Max - Allocation (derived automatically by SystemState).
    5. Conservation: Available[j] + sum_i(Allocation[i][j]) = Total[j].

──────────────────────────────────────────────────────────────────────
DESIGN PRINCIPLES
──────────────────────────────────────────────────────────────────────

Reproducibility
    Every generator accepts an integer seed and uses an isolated
    random.Random instance so global state is never modified and
    results are identical across repeated calls with the same seed.

Structural separation
    - SystemState stores {Total, Max, Allocation} (Banker's view).
    - Request matrices are generated separately and independently
      of Need (Max - Allocation), maintaining the invariant that
      Request != Need in the detection algorithm.

No hardcoded algorithm results
    Generators produce structurally valid states.  Whether a state
    is safe, unsafe, or deadlocked is determined by running the
    actual algorithms — never assumed by the generator.

Benchmark compatibility
    All public functions return plain Python lists and SystemState
    objects; no external dependencies are introduced.

──────────────────────────────────────────────────────────────────────
PUBLIC INTERFACE
──────────────────────────────────────────────────────────────────────

    make_state(n, m, total, seed)
        Random state: Total given, Max and Allocation sampled.

    make_state_with_pressure(n, m, total_per_type, pressure, seed)
        State with controlled per-resource demand pressure rho_j.

    make_zero_request(n, m)
        All-zero Request matrix (no current outstanding requests).

    make_random_request(state, seed)
        Random Request[i][j] in [0, Allocation[i][j]].

    make_deadlock_request(state, seed)
        Request constructed to maximise chance of deadlock.

    make_safe_state(n, m, total_per_type, seed)
        Generate a SystemState verified to have a Banker's safe sequence.

    make_unsafe_state(n, m, total_per_type, seed)
        Generate a SystemState verified to be unsafe (no safe sequence).

    make_deadlocked_workload(n, m, total_per_type, seed)
        Generate a (SystemState, Request) pair verified to be in active deadlock.

    boundary_sweep(n, m, base_max, base_alloc, seed)
        Systematically vary Total[j] from minimum to maximum and
        return one (SystemState, rho_j, rho_max) record per step.

    sweep_across_dimensions(process_counts, resource_counts, seed)
        Run boundary sweeps across multiple (n, m) process and resource counts.

    scaling_grid(process_counts, resource_counts, seed)
        Cartesian product of n × m configurations for benchmarking.

    WorkloadSpec (NamedTuple)
        Container returned by scaling_grid entries.

    GeneratorError (Exception)
        Raised for invalid generator arguments.
"""

from __future__ import annotations

import random
from typing import Dict, List, NamedTuple, Tuple

from src.bankers_algorithm import safety_check
from src.deadlock_detector import detect_deadlock
from src.models import InvariantViolation, SystemState


# ═══════════════════════════════════════════════════════════════════════
# Exceptions and Named Containers
# ═══════════════════════════════════════════════════════════════════════


class GeneratorError(Exception):
    """Raised when generator arguments are structurally invalid."""
    pass


class WorkloadSpec(NamedTuple):
    """
    A single workload configuration entry from scaling_grid.

    Fields
    ------
    n : int
        Number of processes.
    m : int
        Number of resource types.
    state : SystemState
        A generated and invariant-validated system state.
    seed : int
        The seed used to generate this workload.
    """
    n: int
    m: int
    state: SystemState
    seed: int


class BoundarySweepPoint(NamedTuple):
    """
    One data point in a boundary sweep.

    Fields
    ------
    step : int
        Sweep step index (0-based).
    total : list[int]
        Total resource vector at this step.
    available : list[int]
        Available resources after allocations are deducted.
    state : SystemState
        The validated system state at this capacity level.
    rho : list[float]
        Per-resource pressure metrics rho_j = sum(Need[i][j]) / Total[j].
    rho_max : float
        Maximum per-resource pressure (bottleneck metric).
    """
    step: int
    total: List[int]
    available: List[int]
    state: SystemState
    rho: List[float]
    rho_max: float


# ═══════════════════════════════════════════════════════════════════════
# Private Helpers
# ═══════════════════════════════════════════════════════════════════════


def _validate_dimensions(n: int, m: int) -> None:
    """Raise GeneratorError if n or m are non-positive integers."""
    if not isinstance(n, int) or n < 1:
        raise GeneratorError(
            f"n={n!r} must be a positive integer (number of processes)."
        )
    if not isinstance(m, int) or m < 1:
        raise GeneratorError(
            f"m={m!r} must be a positive integer (number of resource types)."
        )


def _validate_total(total: List[int], m: int) -> None:
    """Raise GeneratorError if total vector is structurally invalid."""
    if len(total) != m:
        raise GeneratorError(
            f"total has {len(total)} elements; expected m={m}."
        )
    for j, t in enumerate(total):
        if not isinstance(t, int) or t < 1:
            raise GeneratorError(
                f"total[{j}]={t!r} must be a positive integer."
            )


def _make_rng(seed: int) -> random.Random:
    """Return an isolated Random instance for the given seed."""
    if not isinstance(seed, int):
        raise GeneratorError(f"seed={seed!r} must be an integer.")
    return random.Random(seed)


# ═══════════════════════════════════════════════════════════════════════
# State Generation
# ═══════════════════════════════════════════════════════════════════════


def make_state(
    n: int,
    m: int,
    total: List[int],
    seed: int = 42,
) -> SystemState:
    """
    Generate a random but invariant-valid SystemState.

    For each process i and resource type j:
        Max[i][j]        ~ Uniform[1, Total[j]]
        Allocation[i][j] ~ Uniform[0, min(Max[i][j], budget_j)]

    where budget_j is the remaining unallocated capacity for resource j,
    ensuring the conservation invariant Available[j] >= 0.

    Parameters
    ----------
    n : int
        Number of processes (>= 1).
    m : int
        Number of resource types (>= 1).
    total : list[int]
        Total instances of each resource type.  Length m; all >= 1.
    seed : int
        PRNG seed for deterministic reproducibility.

    Returns
    -------
    SystemState
        A validated system state.

    Raises
    ------
    GeneratorError
        If n, m, or total are structurally invalid.
    """
    _validate_dimensions(n, m)
    _validate_total(total, m)
    rng = _make_rng(seed)

    # Generate Max freely (each process may claim up to Total[j]).
    max_claim = [
        [rng.randint(1, total[j]) for j in range(m)]
        for _ in range(n)
    ]

    # Generate Allocation respecting conservation: track remaining budget.
    remaining = list(total)   # available to allocate across all processes
    allocation = [[0] * m for _ in range(n)]

    # Shuffle process order so budget isn't systematically biased toward P0.
    process_order = list(range(n))
    rng.shuffle(process_order)

    for i in process_order:
        for j in range(m):
            # Cap allocation at both Max claim and remaining budget.
            cap = min(max_claim[i][j], remaining[j])
            allocation[i][j] = rng.randint(0, cap)
            remaining[j] -= allocation[i][j]

    return SystemState(
        total=total,
        max_claim=max_claim,
        allocation=allocation,
    )


def make_state_with_pressure(
    n: int,
    m: int,
    total_per_type: int,
    pressure: float,
    seed: int = 42,
) -> SystemState:
    """
    Generate a SystemState with a target per-resource demand pressure.

    The pressure parameter controls the ratio of total outstanding
    demand (sum of Need values) to total system capacity:

        rho_j = sum_i(Need[i][j]) / Total[j]  ≈ pressure

    This is a TARGET, not a guarantee.  The generator approaches the
    target by scaling Max values, but integer rounding means the actual
    rho_j values may differ slightly.  Callers should read
    state.resource_pressure() for the actual values.

    rho_j > 1.0 is valid and expected at high pressure — it means the
    combined worst-case demand exceeds total capacity, which is
    numerically possible when processes share a pool.

    Parameters
    ----------
    n : int
        Number of processes (>= 1).
    m : int
        Number of resource types (>= 1).
    total_per_type : int
        Total instances per resource type (same for all types; >= 1).
    pressure : float
        Target demand pressure (rho).  Must be > 0.  Values > 1.0
        are allowed and meaningful (over-subscribed demand).
    seed : int
        PRNG seed.

    Returns
    -------
    SystemState
        A validated system state approaching the target pressure.

    Raises
    ------
    GeneratorError
        If arguments are invalid.
    """
    _validate_dimensions(n, m)
    if not isinstance(total_per_type, int) or total_per_type < 1:
        raise GeneratorError(
            f"total_per_type={total_per_type!r} must be a positive integer."
        )
    if not isinstance(pressure, (int, float)) or pressure <= 0:
        raise GeneratorError(
            f"pressure={pressure!r} must be a positive number."
        )

    rng = _make_rng(seed)
    total = [total_per_type] * m

    # Target total Need per column = pressure * total_per_type.
    # Distribute across n processes using random splits.
    target_need_total = pressure * total_per_type

    allocation = [[0] * m for _ in range(n)]
    max_claim   = [[0] * m for _ in range(n)]

    remaining_budget = list(total)   # for conservation

    for j in range(m):
        # Generate n non-negative Need values summing near target.
        # Use Dirichlet-like split: draw n uniform values and normalise.
        raw = [rng.random() + 1e-9 for _ in range(n)]
        raw_sum = sum(raw)
        # Scale so sum equals target_need_total, then round to ints.
        need_j = [max(0, round(r / raw_sum * target_need_total)) for r in raw]

        # Assign Allocation and Max for each process.
        # Allocation[i][j] is bounded by remaining conservation budget.
        for i in range(n):
            # Allocation: random share of remaining capacity, capped at need.
            cap = min(need_j[i], remaining_budget[j])
            alloc = rng.randint(0, cap)
            allocation[i][j] = alloc
            remaining_budget[j] -= alloc
            # Max = Allocation + Need.
            max_claim[i][j] = alloc + need_j[i]

    # Clamp Max to Total (Max > Total would violate no invariant directly
    # but is unrealistic; Allocation <= Max is guaranteed by construction).
    for i in range(n):
        for j in range(m):
            # If Need is very large, Max could exceed Total.
            # Clamp Need so Max stays reasonable, keeping Allocation <= Max.
            if max_claim[i][j] > total[j] * 3:   # allow over-subscription
                excess = max_claim[i][j] - total[j] * 3
                max_claim[i][j] = total[j] * 3
                # Reduce Need correspondingly; Allocation is unchanged.

    return SystemState(
        total=total,
        max_claim=max_claim,
        allocation=allocation,
    )


# ═══════════════════════════════════════════════════════════════════════
# Request Matrix Generation
# ═══════════════════════════════════════════════════════════════════════


def make_zero_request(n: int, m: int) -> List[List[int]]:
    """
    Return an all-zero n × m Request matrix.

    Represents a snapshot where no process currently has any
    outstanding unsatisfied resource request.  When used with
    detect_deadlock, this always returns is_deadlocked=False
    (every Request[i] = [0,…,0] <= Work trivially).

    Parameters
    ----------
    n : int   Number of processes.
    m : int   Number of resource types.
    """
    _validate_dimensions(n, m)
    return [[0] * m for _ in range(n)]


def make_random_request(
    state: SystemState,
    seed: int = 42,
) -> List[List[int]]:
    """
    Generate a random Request matrix compatible with the given state.

    Request[i][j] ~ Uniform[0, Allocation[i][j]].

    Rationale: a process can only be waiting for resources it does not
    already hold — the total demand cannot exceed system capacity — so
    capping at Allocation[i][j] produces realistic requests.

    Note: this does NOT enforce Request[i][j] <= Available[j]; the
    detection algorithm handles cases where requests exceed available
    resources (that is precisely when deadlock may occur).

    Parameters
    ----------
    state : SystemState
        The allocation state from which Allocation is read.
    seed : int
        PRNG seed.

    Returns
    -------
    list[list[int]]
        Random request matrix of shape n × m.
    """
    rng = _make_rng(seed)
    allocation = state.allocation   # deep copy via property
    n, m = state.n, state.m
    return [
        [rng.randint(0, allocation[i][j]) for j in range(m)]
        for i in range(n)
    ]


def make_deadlock_request(
    state: SystemState,
    seed: int = 42,
) -> List[List[int]]:
    """
    Generate a Request matrix designed to maximise deadlock probability.

    Strategy: for each process i, set Request[i][j] = Allocation[i][j]
    for all j where Available[j] == 0.  This maximises the number of
    unsatisfiable requests when resources are scarce.  Where Available
    is nonzero, requests are set to zero to avoid trivial satisfaction.

    This does NOT guarantee deadlock — the actual state classification
    must be determined by running detect_deadlock on the returned matrix.

    Parameters
    ----------
    state : SystemState
        The allocation state.
    seed : int
        PRNG seed (used for tie-breaking randomisation).

    Returns
    -------
    list[list[int]]
        A request matrix shaped n × m.
    """
    rng = _make_rng(seed)
    allocation = state.allocation
    available  = state.available
    n, m = state.n, state.m

    request = [[0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            if available[j] == 0 and allocation[i][j] > 0:
                # Request all held resources of a fully-consumed type.
                request[i][j] = allocation[i][j]
            else:
                # Small random request where some capacity is free.
                request[i][j] = rng.randint(0, max(0, allocation[i][j] // 2))
    return request


def make_safe_state(
    n: int,
    m: int,
    total_per_type: int = 20,
    seed: int = 42,
    max_attempts: int = 50,
) -> SystemState:
    """
    Generate a SystemState verified to be safe (a safe sequence exists).

    Uses a low demand-pressure baseline (abundant available resources)
    and verifies safety with the Banker's safety algorithm.

    Parameters
    ----------
    n : int
        Number of processes (>= 1).
    m : int
        Number of resource types (>= 1).
    total_per_type : int
        Total instances per resource type.
    seed : int
        Starting PRNG seed.
    max_attempts : int
        Maximum seeds to try before raising GeneratorError.

    Returns
    -------
    SystemState
        A validated system state guaranteed to be safe.
    """
    _validate_dimensions(n, m)
    for attempt in range(max_attempts):
        candidate_seed = seed + attempt
        state = make_state_with_pressure(
            n=n,
            m=m,
            total_per_type=total_per_type,
            pressure=0.2,
            seed=candidate_seed,
        )
        if safety_check(state).is_safe:
            return state

    raise GeneratorError(
        f"Could not generate a safe state in {max_attempts} attempts for n={n}, m={m}."
    )


def make_unsafe_state(
    n: int,
    m: int,
    total_per_type: int = 10,
    seed: int = 42,
    max_attempts: int = 50,
) -> SystemState:
    """
    Generate a SystemState verified to be unsafe (no safe sequence exists).

    Uses high demand-pressure (resources heavily over-subscribed)
    and verifies with the Banker's safety algorithm that no safe sequence exists.

    Parameters
    ----------
    n : int
        Number of processes (>= 1).
    m : int
        Number of resource types (>= 1).
    total_per_type : int
        Total instances per resource type.
    seed : int
        Starting PRNG seed.
    max_attempts : int
        Maximum seeds to try before raising GeneratorError.

    Returns
    -------
    SystemState
        A validated system state guaranteed to be unsafe.
    """
    _validate_dimensions(n, m)
    for attempt in range(max_attempts):
        candidate_seed = seed + attempt
        state = make_state_with_pressure(
            n=n,
            m=m,
            total_per_type=total_per_type,
            pressure=3.5,
            seed=candidate_seed,
        )
        if not safety_check(state).is_safe:
            return state

    raise GeneratorError(
        f"Could not generate an unsafe state in {max_attempts} attempts for n={n}, m={m}."
    )


def make_deadlocked_workload(
    n: int,
    m: int,
    total_per_type: int = 10,
    seed: int = 42,
    max_attempts: int = 50,
) -> Tuple[SystemState, List[List[int]]]:
    """
    Generate a (SystemState, Request) pair verified to be in active deadlock.

    Uses high demand pressure to deplete available resources and constructs
    unfulfilled circular/blocking requests, verified with detect_deadlock.

    Parameters
    ----------
    n : int
        Number of processes (>= 1).
    m : int
        Number of resource types (>= 1).
    total_per_type : int
        Total instances per resource type.
    seed : int
        Starting PRNG seed.
    max_attempts : int
        Maximum seeds to try before raising GeneratorError.

    Returns
    -------
    tuple[SystemState, list[list[int]]]
        State and Request matrix guaranteed to be in active deadlock.
    """
    _validate_dimensions(n, m)
    for attempt in range(max_attempts):
        candidate_seed = seed + attempt
        state = make_state_with_pressure(
            n=n,
            m=m,
            total_per_type=total_per_type,
            pressure=4.0,
            seed=candidate_seed,
        )
        req = make_deadlock_request(state, seed=candidate_seed)
        if detect_deadlock(state, req).is_deadlocked:
            return state, req

    raise GeneratorError(
        f"Could not generate a deadlocked workload in {max_attempts} attempts for n={n}, m={m}."
    )


# ═══════════════════════════════════════════════════════════════════════
# Systematic Boundary Sweep
# ═══════════════════════════════════════════════════════════════════════


def boundary_sweep(
    n: int,
    m: int,
    base_max: List[List[int]],
    base_alloc: List[List[int]],
    seed: int = 42,
) -> List[BoundarySweepPoint]:
    """
    Systematically vary Total[j] while preserving all matrix invariants.

    For each step, Total[j] is increased by 1 unit per resource type,
    starting from the minimum feasible value:

        Total_min[j] = sum_i(Allocation[i][j])  (Available = 0)

    up to:

        Total_max[j] = sum_i(Max[i][j])          (Max fully satisfiable)

    At each step a new SystemState is constructed with
        Total[j] = Total_min[j] + step
    and Available[j] = Total[j] - sum_i(Allocation[i][j]).

    This directly tests how Available capacity changes the resource-
    pressure metrics rho_j and rho_max as defined in the plan:

        rho_j = sum_i(Need[i][j]) / Total[j]

    The boundary at which the system transitions from safe to unsafe
    is NOT determined by the generator — callers should run
    safety_check on each returned state.

    Parameters
    ----------
    n : int
        Number of processes.
    m : int
        Number of resource types.
    base_max : list[list[int]]
        Max claim matrix.  Shape n × m.  Validated on construction.
    base_alloc : list[list[int]]
        Allocation matrix.  Shape n × m.  Validated on construction.
    seed : int
        PRNG seed (not used for generation but stored for traceability).

    Returns
    -------
    list[BoundarySweepPoint]
        One entry per sweep step, ordered from minimum to maximum capacity.

    Raises
    ------
    GeneratorError
        If n, m, base_max or base_alloc are structurally invalid.
    InvariantViolation
        If base_max or base_alloc violate SystemState invariants.
    """
    _validate_dimensions(n, m)

    # Validate input matrix dimensions manually before constructing states.
    if len(base_max) != n:
        raise GeneratorError(
            f"base_max has {len(base_max)} rows; expected n={n}."
        )
    if len(base_alloc) != n:
        raise GeneratorError(
            f"base_alloc has {len(base_alloc)} rows; expected n={n}."
        )
    for i in range(n):
        if len(base_max[i]) != m:
            raise GeneratorError(
                f"base_max[{i}] has {len(base_max[i])} columns; expected m={m}."
            )
        if len(base_alloc[i]) != m:
            raise GeneratorError(
                f"base_alloc[{i}] has {len(base_alloc[i])} columns; expected m={m}."
            )

    # Minimum Total: exactly the amount already allocated.
    alloc_sums = [
        sum(base_alloc[i][j] for i in range(n))
        for j in range(m)
    ]
    # Maximum Total: enough for every Max claim (fully satisfiable).
    max_sums = [
        sum(base_max[i][j] for i in range(n))
        for j in range(m)
    ]

    # Number of steps = max over all resource types of the range.
    n_steps = max(max_sums[j] - alloc_sums[j] for j in range(m)) + 1

    points: List[BoundarySweepPoint] = []

    for step in range(n_steps):
        # Build Total for this step: clamp at max_sums per resource type.
        total = [
            min(alloc_sums[j] + step, max_sums[j])
            for j in range(m)
        ]
        # Ensure Total >= 1 for every resource type (SystemState invariant).
        total = [max(t, 1) for t in total]

        try:
            state = SystemState(
                total=total,
                max_claim=base_max,
                allocation=base_alloc,
            )
        except InvariantViolation:
            # Skip steps where the state cannot be constructed
            # (e.g., Max > Total when clamping is insufficient).
            continue

        rho = state.resource_pressure()
        rho_max = state.max_pressure()

        points.append(BoundarySweepPoint(
            step=step,
            total=list(total),
            available=state.available,
            state=state,
            rho=rho,
            rho_max=rho_max,
        ))

    return points


def sweep_across_dimensions(
    process_counts: List[int],
    resource_counts: List[int],
    seed: int = 42,
) -> Dict[Tuple[int, int], List[BoundarySweepPoint]]:
    """
    Run systematic boundary sweeps across multiple process (n) and resource (m) counts.

    For each (n, m) pair in the grid:
        1. Generates a base SystemState with reproducible seed.
        2. Executes a boundary sweep from minimum to maximum capacity.
        3. Records the list of BoundarySweepPoint points.

    Parameters
    ----------
    process_counts : list[int]
        Process counts to sweep over.
    resource_counts : list[int]
        Resource counts to sweep over.
    seed : int
        Base PRNG seed.

    Returns
    -------
    dict[tuple[int, int], list[BoundarySweepPoint]]
        Mapping of (n, m) -> list of sweep points.
    """
    if not process_counts:
        raise GeneratorError("process_counts must not be empty.")
    if not resource_counts:
        raise GeneratorError("resource_counts must not be empty.")

    results: Dict[Tuple[int, int], List[BoundarySweepPoint]] = {}
    for n in process_counts:
        for m in resource_counts:
            _validate_dimensions(n, m)
            config_seed = seed + n * 1000 + m
            total = [max(n, 10)] * m
            base_state = make_state(n=n, m=m, total=total, seed=config_seed)
            points = boundary_sweep(
                n=n,
                m=m,
                base_max=base_state.max_claim,
                base_alloc=base_state.allocation,
                seed=config_seed,
            )
            results[(n, m)] = points

    return results


# ═══════════════════════════════════════════════════════════════════════
# Scaling Grid for Benchmarking
# ═══════════════════════════════════════════════════════════════════════


def scaling_grid(
    process_counts: List[int],
    resource_counts: List[int],
    seed: int = 42,
) -> List[WorkloadSpec]:
    """
    Generate one WorkloadSpec per (n, m) pair in the Cartesian product.

    Each configuration uses a unique seed derived from the base seed
    and the (n, m) pair, so configurations are independent and
    reproducible.

    Total resources per type are set to max(n, 10) to ensure there is
    enough capacity to distribute across processes without saturation.

    This is the primary input for the Phase 5 benchmark harness.

    Parameters
    ----------
    process_counts : list[int]
        List of process counts to include.  Each >= 1.
    resource_counts : list[int]
        List of resource type counts to include.  Each >= 1.
    seed : int
        Base PRNG seed.

    Returns
    -------
    list[WorkloadSpec]
        One entry per (n, m) combination, ordered by n then m.

    Raises
    ------
    GeneratorError
        If any count is invalid.
    """
    if not process_counts:
        raise GeneratorError("process_counts must not be empty.")
    if not resource_counts:
        raise GeneratorError("resource_counts must not be empty.")

    specs: List[WorkloadSpec] = []

    for n in process_counts:
        for m in resource_counts:
            _validate_dimensions(n, m)
            # Derive a unique seed per (n, m) so configurations do not
            # share PRNG state and results are independently reproducible.
            config_seed = seed + n * 1000 + m
            total = [max(n, 10)] * m
            state = make_state(n=n, m=m, total=total, seed=config_seed)
            specs.append(WorkloadSpec(n=n, m=m, state=state, seed=config_seed))

    return specs

