"""
CA2 - Deadlock Detection and Avoidance
Multi-Instance Deadlock Detection Algorithm.

This module implements the standard multi-instance resource deadlock
detection algorithm described in Silberschatz et al.,
"Operating System Concepts", Chapter 8 (§8.6).

──────────────────────────────────────────────────────────────────────
CRITICAL DISTINCTION FROM BANKER'S ALGORITHM (Phase 2)
──────────────────────────────────────────────────────────────────────

    Banker's Safety Algorithm (bankers_algorithm.py)
        Uses: Available, Allocation, Need  (Max - Allocation)
        Purpose: Proactive — called on every resource request to
                 determine whether granting would leave the system
                 in a state from which all processes can EVENTUALLY
                 complete under worst-case claims.
        Question: "Is this state safe?"

    Multi-Instance Detection Algorithm (this module)
        Uses: Available, Allocation, Request
        Purpose: Reactive — called periodically or on demand to
                 determine whether any processes are CURRENTLY
                 permanently blocked by their outstanding requests.
        Question: "Is there a deadlock RIGHT NOW?"

    Request[i][j]  ≠  Need[i][j]
        Request is the ACTUAL outstanding unsatisfied request at
        audit time.  Need is the MAXIMUM future claim.  These are
        fundamentally different quantities and must never be
        substituted for each other.

──────────────────────────────────────────────────────────────────────
ALGORITHM (Silberschatz §8.6.1)
──────────────────────────────────────────────────────────────────────

Inputs:
    Available[m]      — currently available instances per resource type.
    Allocation[n][m]  — resources currently held by each process.
    Request[n][m]     — outstanding unsatisfied requests per process.

Steps:
    1.  Work  = copy(Available).
    2.  For each process i:
            Finish[i] = True  if Allocation[i] == [0, …, 0]
                       False  otherwise.
        Rationale: a process holding no resources cannot be part of
        a deadlock cycle; it can be treated as already finished.
    3.  Find index i such that:
            Finish[i] == False  AND
            Request[i][j] <= Work[j]  for all j.
    4.  If found:
            Work[j] += Allocation[i][j]  for all j.
            Finish[i] = True.
            Go to step 3.
    5.  If not found: terminate.
    6.  Result:
            is_deadlocked = any(Finish[i] == False)
            deadlocked_processes = {i | Finish[i] == False}

Worst-case time complexity: O(m × n²)
    — identical asymptotic bound to the Banker's safety algorithm,
      but incurred only when detection is invoked, not on every
      resource request.

──────────────────────────────────────────────────────────────────────
INTERFACES
──────────────────────────────────────────────────────────────────────

    detect_deadlock(state, request) -> DetectionResult
        Main entry point.  Takes a SystemState (Allocation and
        Available are read from it) and a separate Request matrix.

    DetectionResult (frozen dataclass)
        is_deadlocked         bool
        deadlocked_processes  list[int]   — sorted process indices
        trace                 list[dict]  — step-by-step audit log

    DetectionError (exception)
        Raised for structural violations in the Request argument:
        wrong dimensions, non-integer values, or negative values.
        Never raised for a detected deadlock — that is a valid result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.models import SystemState


# ═══════════════════════════════════════════════════════════════════════
# Result and Error Types
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DetectionResult:
    """
    Result of a multi-instance deadlock detection check.

    Attributes
    ----------
    is_deadlocked : bool
        True if one or more processes are permanently blocked.
    deadlocked_processes : list[int]
        Sorted list of process indices for which Finish[i] == False
        at algorithm termination.  Empty when is_deadlocked is False.
    trace : list[dict]
        Step-by-step execution trace suitable for logging, debugging,
        and inclusion in experiment reports.

    Notes
    -----
    The dataclass is frozen to prevent post-construction mutation.
    The list fields are stored as plain lists; callers who need
    guaranteed immutability should copy them before storing externally.
    """

    is_deadlocked: bool
    deadlocked_processes: List[int]
    trace: List[Dict[str, Any]]


class DetectionError(Exception):
    """
    Raised when the Request argument has structural violations.

    Examples of violations:
        - Wrong number of rows (must equal state.n).
        - Wrong row length (must equal state.m).
        - Non-integer or negative entry values.

    This is raised for programming errors in how detection is called,
    not for the presence of a deadlock (which is a normal result).
    """

    pass


# ═══════════════════════════════════════════════════════════════════════
# Validation Helper
# ═══════════════════════════════════════════════════════════════════════


def _validate_request_matrix(
    request: List[List[int]],
    n: int,
    m: int,
) -> None:
    """
    Validate the structural integrity of the Request matrix.

    Parameters
    ----------
    request : list[list[int]]
        The request matrix to validate.
    n : int
        Expected number of rows (processes).
    m : int
        Expected number of columns (resource types).

    Raises
    ------
    DetectionError
        If the matrix has wrong dimensions, non-integer values,
        or negative values.
    """
    if len(request) != n:
        raise DetectionError(
            f"Request matrix has {len(request)} rows; "
            f"expected n={n} (matching state.n)."
        )
    for i, row in enumerate(request):
        if len(row) != m:
            raise DetectionError(
                f"Request[{i}] has {len(row)} columns; "
                f"expected m={m} (matching state.m)."
            )
        for j, val in enumerate(row):
            if not isinstance(val, int) or isinstance(val, bool):
                raise DetectionError(
                    f"Request[{i}][{j}] = {val!r} must be a "
                    f"non-negative integer."
                )
            if val < 0:
                raise DetectionError(
                    f"Request[{i}][{j}] = {val} is negative."
                )


# ═══════════════════════════════════════════════════════════════════════
# Detection Algorithm
# ═══════════════════════════════════════════════════════════════════════


def detect_deadlock(
    state: SystemState,
    request: List[List[int]],
) -> DetectionResult:
    """
    Multi-instance deadlock detection algorithm.

    Determines whether any processes are currently deadlocked by
    examining their outstanding requests against available resources.

    Parameters
    ----------
    state : SystemState
        A validated system state.  Provides Available[m] and
        Allocation[n][m].  The Max and Need matrices stored in state
        are NOT used by this algorithm — detection uses only current
        actual requests, not worst-case claims.
    request : list[list[int]]
        The Request matrix.  Shape n × m.  Request[i][j] is the number
        of instances of resource type j that process i is currently
        waiting for.  This is an audit-time snapshot — it is
        deep-copied internally so external mutation does not affect
        the algorithm.

        IMPORTANT: Request[i][j] is NOT the same as Need[i][j].
            Need = Max - Allocation  (maximum future claim, Banker's)
            Request = outstanding unsatisfied request (detection)

    Returns
    -------
    DetectionResult
        Contains is_deadlocked, deadlocked_processes, and trace.

    Raises
    ------
    DetectionError
        If the Request argument has structural violations.

    Notes
    -----
    Worst-case time complexity: O(m × n²).
    The state argument (SystemState) is never modified.
    """
    n = state.n
    m = state.m

    # ── Validate and deep-copy the Request matrix ─────────────────────
    # Validation first, then copy, so we never store an invalid matrix.
    _validate_request_matrix(request, n, m)
    req: List[List[int]] = [list(row) for row in request]

    # ── Read derived state values (all property calls return copies) ──
    work: List[int] = state.available
    allocation: List[List[int]] = state.allocation

    trace: List[Dict[str, Any]] = []

    # ── Step 1 & 2: Initialise Work and Finish ────────────────────────
    # Finish[i] = True  iff process i holds no resources.
    # Such processes cannot be part of a deadlock cycle because they
    # have nothing to offer in an exchange — they are already free.
    finish: List[bool] = [
        all(allocation[i][j] == 0 for j in range(m))
        for i in range(n)
    ]

    trace.append({
        "step": "init",
        "work": list(work),
        "finish": list(finish),
        "note": (
            "Finish[i]=True where Allocation[i] is all-zero "
            "(process holds no resources)."
        ),
    })

    # ── Steps 3–5: Iterative search ───────────────────────────────────
    # Outer loop: at most n iterations (one process finishes per pass).
    for iteration in range(n):
        found = False

        # Inner loop: scan all processes for one that can proceed.
        for i in range(n):
            if finish[i]:
                continue

            # Can process i's current request be satisfied?
            if all(req[i][j] <= work[j] for j in range(m)):
                # Simulate process i completing: release its allocation.
                work_before = list(work)
                for j in range(m):
                    work[j] += allocation[i][j]
                finish[i] = True

                trace.append({
                    "step": f"iteration_{iteration + 1}",
                    "selected_process": i,
                    "request_i": list(req[i]),
                    "allocation_i": list(allocation[i]),
                    "work_before": work_before,
                    "work_after": list(work),
                    "finish": list(finish),
                })

                found = True
                break  # Restart inner scan from process 0.

        if not found:
            # No unfinished process can satisfy its current request.
            trace.append({
                "step": f"terminated_at_iteration_{iteration + 1}",
                "reason": "no_eligible_process",
                "work": list(work),
                "finish": list(finish),
            })
            break

    # ── Step 6: Identify deadlocked processes ─────────────────────────
    deadlocked: List[int] = sorted(
        i for i in range(n) if not finish[i]
    )
    is_deadlocked: bool = bool(deadlocked)

    if is_deadlocked:
        trace.append({
            "step": "result",
            "is_deadlocked": True,
            "deadlocked_processes": list(deadlocked),
            "final_work": list(work),
        })
    else:
        trace.append({
            "step": "result",
            "is_deadlocked": False,
            "deadlocked_processes": [],
            "final_work": list(work),
        })

    return DetectionResult(
        is_deadlocked=is_deadlocked,
        deadlocked_processes=deadlocked,
        trace=trace,
    )

