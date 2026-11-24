"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/detectors/multi_instance_detector.py

Multi-Instance Deadlock Detection Algorithm.
Implements the standard algorithm from Silberschatz, Galvin & Gagne,
"Operating System Concepts", Chapter 8 (§8.6).

Theoretical Specification:
1. Work Vector:
   Work = copy(Available)
2. Finish Vector Initialization:
   For i = 0, ..., n-1:
       Finish[i] = True  if Allocation[i] == [0, ..., 0]
       Finish[i] = False otherwise.
   (Processes holding no resources cannot be part of an unresolvable circular lock).
3. Search Step:
   Find an index i such that:
       Finish[i] == False AND Request[i][j] <= Work[j] for all j in {0, ..., m-1}.
4. Update Step:
   If found:
       Work[j] += Allocation[i][j] for all j.
       Finish[i] = True.
       Repeat step 3.
5. Termination & Verdict:
   If no such i exists, terminate.
   is_deadlocked = any(Finish[i] == False)
   deadlocked_processes = [i for i in range(n) if not Finish[i]]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.models import SystemState


@dataclass(frozen=True)
class MultiInstanceResult:
    """
    Structured immutable result of Multi-Instance Deadlock Detection.

    Attributes
    ----------
    is_deadlocked : bool
        True if at least one process remained unfinished.
    deadlocked_processes : List[int]
        Sorted list of process indices that could not finish under current requests.
    finish_order : List[int]
        Order in which processes satisfied requests and released resources.
    unallocated_processes : List[int]
        Processes with zero allocation that were marked finished at step 2.
    work_history : List[List[int]]
        Snapshot of Work vector at each allocation recovery step.
    final_work : List[int]
        Final state of the Work vector upon algorithm termination.
    trace : List[Dict[str, Any]]
        Chronological audit log of decisions made at each step.
    """
    is_deadlocked: bool
    deadlocked_processes: List[int]
    finish_order: List[int]
    unallocated_processes: List[int]
    work_history: List[List[int]]
    final_work: List[int]
    trace: List[Dict[str, Any]]


def detect_multi_instance_deadlock(state: SystemState) -> MultiInstanceResult:
    """
    Executes the standard multi-instance deadlock detection algorithm on a SystemState.

    Parameters
    ----------
    state : SystemState
        The system resource allocation state to inspect.

    Returns
    -------
    MultiInstanceResult
        Structured detection result detailing deadlock status, process classifications,
        finish sequences, and work evolution.
    """
    n = state.n
    m = state.m
    allocation = state.allocation
    request = state.request
    available = state.available

    # Step 1: Work = copy(Available)
    work: List[int] = list(available)
    work_history: List[List[int]] = [list(work)]
    trace: List[Dict[str, Any]] = []

    # Step 2: Initialize Finish vector based on Allocation
    finish: List[bool] = [False] * n
    unallocated_processes: List[int] = []

    for i in range(n):
        if all(allocation[i][j] == 0 for j in range(m)):
            finish[i] = True
            unallocated_processes.append(i)

    trace.append({
        "step": "initialization",
        "work": list(work),
        "unallocated_processes": list(unallocated_processes),
        "finish_initial": list(finish),
    })

    finish_order: List[int] = []

    # Steps 3 & 4: Iteratively find an unfinished process whose Request <= Work
    while True:
        found_process: bool = False

        for i in range(n):
            if not finish[i]:
                # Check condition: Request[i][j] <= Work[j] for all j
                can_proceed = all(request[i][j] <= work[j] for j in range(m))

                if can_proceed:
                    # Process i can be satisfied; pretend it finishes and releases resources
                    for j in range(m):
                        work[j] += allocation[i][j]

                    finish[i] = True
                    finish_order.append(i)
                    work_history.append(list(work))
                    found_process = True

                    trace.append({
                        "step": "process_finished",
                        "process": i,
                        "request": list(request[i]),
                        "released_allocation": list(allocation[i]),
                        "new_work": list(work),
                    })
                    # Restart search to respect updated Work
                    break

        if not found_process:
            break

    # Step 5: Evaluate deadlocked processes
    deadlocked_processes = [i for i in range(n) if not finish[i]]
    is_deadlocked = len(deadlocked_processes) > 0

    trace.append({
        "step": "termination",
        "is_deadlocked": is_deadlocked,
        "deadlocked_processes": list(deadlocked_processes),
        "finish_final": list(finish),
        "final_work": list(work),
    })

    return MultiInstanceResult(
        is_deadlocked=is_deadlocked,
        deadlocked_processes=deadlocked_processes,
        finish_order=finish_order,
        unallocated_processes=unallocated_processes,
        work_history=work_history,
        final_work=work,
        trace=trace,
    )
