"""
CA2 - Deadlock Detection and Avoidance
Banker's Algorithm: Safety Algorithm and Resource-Request Algorithm.

The Safety Algorithm determines whether a system state is safe by
attempting to find a safe sequence — an ordering in which all processes
can complete by acquiring their maximum remaining claims.

The Resource-Request Algorithm handles a dynamic resource request from
a process by:
    1. Validating the request against the process's remaining Need.
    2. Checking whether sufficient resources are currently Available.
    3. Simulating a pretend allocation.
    4. Running the Safety Algorithm on the pretended state.
    5. Granting the request only if the resulting state is safe;
       otherwise discarding the pretended state (rollback).

Worst-case time complexity for both algorithms: O(m × n²), where
n = number of processes and m = number of resource types.

    The outer loop of the safety algorithm runs at most n times
    (one process finishes per pass).  Each pass scans up to n
    unfinished processes, performing an m-element vector comparison
    per process.  Total: O(n × n × m) = O(m × n²).

These algorithms use ONLY the Banker's data structures:
    Available, Max, Allocation, Need.
They do NOT use a Request matrix (that belongs to the detection
algorithm, implemented separately in deadlock_detector.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.models import InvariantViolation, SystemState


# ═══════════════════════════════════════════════════════════════════════
# Result Types
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SafetyResult:
    """
    Result of a Banker's Safety Algorithm check.

    Attributes
    ----------
    is_safe : bool
        True if a safe sequence exists.
    safe_sequence : list[int]
        Ordered process indices forming the safe sequence.
        Empty if the state is unsafe.
    trace : list[dict]
        Step-by-step execution trace for logging and verification.
    """

    is_safe: bool
    safe_sequence: List[int]
    trace: List[Dict[str, Any]]


@dataclass(frozen=True)
class RequestResult:
    """
    Result of a Banker's Resource-Request Algorithm evaluation.

    Attributes
    ----------
    granted : bool
        True if the request was granted.
    new_state : SystemState or None
        The committed system state after granting.  None if denied.
    reason : str
        Human-readable explanation of the outcome.
    details : dict
        Precondition checks, pretend-state values, and safety result.
    """

    granted: bool
    new_state: Optional[SystemState]
    reason: str
    details: Dict[str, Any]


class RequestError(Exception):
    """
    Raised when a resource request violates structural preconditions.

    This indicates a programming error or protocol violation, not a
    normal wait condition.  Examples:
        - Invalid process ID.
        - Wrong request vector length.
        - Request exceeds the process's declared maximum claim (Need).
        - Non-integer or negative request values.
    """

    pass


# ═══════════════════════════════════════════════════════════════════════
# Safety Algorithm
# ═══════════════════════════════════════════════════════════════════════


def safety_check(state: SystemState) -> SafetyResult:
    """
    Banker's Safety Algorithm.

    Determines whether the given system state is safe by searching for
    a safe sequence — an ordering <P_s0, P_s1, ..., P_s(n-1)> such that
    each process's remaining Need can be satisfied by the currently
    available resources plus the resources released by all processes
    that precede it in the sequence.

    Algorithm (Silberschatz, Chapter 8):
        1.  Let Work = Available (copy), Finish = [False] × n.
        2.  Find i such that Finish[i] == False AND Need[i] <= Work.
        3.  If found: Work += Allocation[i], Finish[i] = True.
            Append i to the safe sequence.  Go to step 2.
        4.  If not found: terminate.
        5.  If all Finish[i] == True → Safe; else → Unsafe.

    Worst-case complexity: O(m × n²).

    Parameters
    ----------
    state : SystemState
        A validated system state with enforced invariants.

    Returns
    -------
    SafetyResult
        Contains is_safe, safe_sequence, and a step-by-step trace.
    """
    n = state.n
    m = state.m
    work = state.available          # property returns a copy
    finish = [False] * n
    need = state.need               # property returns a deep copy
    allocation = state.allocation   # property returns a deep copy

    safe_sequence: List[int] = []
    trace: List[Dict[str, Any]] = []

    # Record initial state.
    trace.append({
        "step": "init",
        "work": list(work),
        "finish": list(finish),
    })

    # Outer loop: at most n iterations (one process finishes per pass).
    for iteration in range(n):
        found = False

        # Inner loop: scan all processes for an eligible one.
        for i in range(n):
            if finish[i]:
                continue

            # Check Need[i] <= Work (component-wise).
            if all(need[i][j] <= work[j] for j in range(m)):
                # Process i can complete: reclaim its allocated resources.
                work_before = list(work)
                for j in range(m):
                    work[j] += allocation[i][j]
                finish[i] = True
                safe_sequence.append(i)

                trace.append({
                    "step": f"iteration_{iteration + 1}",
                    "selected_process": i,
                    "need_i": list(need[i]),
                    "work_before": work_before,
                    "allocation_i": list(allocation[i]),
                    "work_after": list(work),
                    "finish": list(finish),
                })

                found = True
                break  # Restart the inner scan from process 0.

        if not found:
            # No unfinished process can proceed; terminate.
            break

    is_safe = all(finish)

    if is_safe:
        trace.append({
            "step": "completed",
            "safe_sequence": list(safe_sequence),
            "final_work": list(work),
        })
    else:
        unfinished = [i for i in range(n) if not finish[i]]
        trace.append({
            "step": "terminated",
            "reason": "no_eligible_process",
            "unfinished_processes": unfinished,
        })

    return SafetyResult(
        is_safe=is_safe,
        safe_sequence=safe_sequence,
        trace=trace,
    )


# ═══════════════════════════════════════════════════════════════════════
# Resource-Request Algorithm
# ═══════════════════════════════════════════════════════════════════════


def request_resources(
    state: SystemState,
    process_id: int,
    request: List[int],
) -> RequestResult:
    """
    Banker's Resource-Request Algorithm.

    Evaluates whether granting a resource request from a specific
    process would leave the system in a safe state.

    Algorithm (Silberschatz, Chapter 8):
        1.  If Request > Need[i] → Error (exceeds maximum claim).
        2.  If Request > Available → Deny (must wait; not an error).
        3.  Pretend allocation:
                Available  -= Request
                Allocation[i] += Request
                Need[i]    -= Request
        4.  Run Safety Algorithm on the pretended state.
        5.  If safe → Grant (return the committed new state).
        6.  If unsafe → Deny (discard the pretended state).

    The pretended state is constructed as a new SystemState object.
    Because SystemState is constructed from (Total, Max, Allocation)
    and derives Available and Need internally with full invariant
    validation, rollback is implicit: if the safety check fails,
    the pretended SystemState is simply not returned.

    Parameters
    ----------
    state : SystemState
        Current validated system state.
    process_id : int
        Index of the requesting process (0 to n-1).
    request : list[int]
        Resource request vector of length m.

    Returns
    -------
    RequestResult
        Contains granted, new_state (if granted), reason, and details.

    Raises
    ------
    RequestError
        If the request violates structural preconditions (invalid
        process ID, wrong vector length, request exceeds Need, or
        non-integer/negative values).
    """
    n = state.n
    m = state.m
    details: Dict[str, Any] = {}

    # ── Structural validation ────────────────────────────────────────

    if not isinstance(process_id, int) or process_id < 0 or process_id >= n:
        raise RequestError(
            f"Invalid process_id={process_id!r}; must be in [0, {n - 1}]."
        )

    if len(request) != m:
        raise RequestError(
            f"Request vector length {len(request)} != m={m}."
        )

    for j in range(m):
        if not isinstance(request[j], int) or request[j] < 0:
            raise RequestError(
                f"Request[{j}]={request[j]!r} must be a non-negative integer."
            )

    need = state.need
    available = state.available

    details["process_id"] = process_id
    details["request"] = list(request)
    details["need_i"] = list(need[process_id])
    details["available_before"] = list(available)

    # ── Precondition 1: Request <= Need[i] ───────────────────────────
    # Violation is a protocol error (process exceeds its declared claim).

    for j in range(m):
        if request[j] > need[process_id][j]:
            raise RequestError(
                f"Request[{j}]={request[j]} exceeds "
                f"Need[{process_id}][{j}]={need[process_id][j]}. "
                f"Process P{process_id} has exceeded its maximum claim."
            )

    details["request_within_need"] = True

    # ── Precondition 2: Request <= Available ──────────────────────────
    # Violation means the process must wait; this is not an error.

    insufficient: List[str] = []
    for j in range(m):
        if request[j] > available[j]:
            insufficient.append(
                f"R{j}: requested {request[j]}, available {available[j]}"
            )

    if insufficient:
        details["request_within_available"] = False
        details["insufficient_resources"] = insufficient
        return RequestResult(
            granted=False,
            new_state=None,
            reason=(
                f"Insufficient resources: process P{process_id} must wait. "
                + "; ".join(insufficient)
            ),
            details=details,
        )

    details["request_within_available"] = True

    # ── Pretend allocation ───────────────────────────────────────────
    # Construct a new SystemState with the request tentatively granted.
    # SystemState validates all invariants on construction (including
    # conservation, non-negativity, and Allocation <= Max), so if the
    # constructor succeeds the pretended state is structurally valid.
    #
    # Rollback is implicit: if the safety check fails, the pretended
    # SystemState object is simply not returned to the caller.

    new_allocation = state.allocation  # deep copy via property
    for j in range(m):
        new_allocation[process_id][j] += request[j]

    pretend_state = SystemState(
        total=state.total,
        max_claim=state.max_claim,
        allocation=new_allocation,
    )

    details["pretend_available"] = pretend_state.available
    details["pretend_allocation_i"] = pretend_state.allocation[process_id]
    details["pretend_need_i"] = pretend_state.need[process_id]

    # ── Safety check on pretended state ──────────────────────────────

    safety_result = safety_check(pretend_state)
    details["safety_result"] = {
        "is_safe": safety_result.is_safe,
        "safe_sequence": safety_result.safe_sequence,
    }

    if safety_result.is_safe:
        seq_str = ", ".join(f"P{p}" for p in safety_result.safe_sequence)
        return RequestResult(
            granted=True,
            new_state=pretend_state,
            reason=(
                f"Request granted: system remains safe with "
                f"sequence <{seq_str}>."
            ),
            details=details,
        )
    else:
        details["rollback"] = True
        return RequestResult(
            granted=False,
            new_state=None,
            reason=(
                f"Request denied: granting would leave system in "
                f"unsafe state. Pretended allocation discarded."
            ),
            details=details,
        )

