"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/ground_truth.py

Standardized ground-truth validation cases for single-instance and multi-instance
deadlock detection algorithms.

Includes explicit test cases for:
1. No Deadlock: Acyclic dependencies, processes complete sequentially.
2. One Deadlock Cycle: Classical 2-process cyclic wait.
3. Multiple Deadlock Cycles: Two independent or overlapping deadlock cycles.
4. Blocked Behind Deadlocked: Processes that wait on a deadlock cycle but are NOT
   part of the cycle themselves.
5. Multiple Resource Instances: Canonical multi-instance resource systems (Silberschatz §8.6).
6. Zero Allocation: Processes holding no resources initialized to Finish=True.
7. Available Headroom: Cycles prevented because Available resources can satisfy requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.models import SystemState


@dataclass(frozen=True)
class GroundTruthCase:
    """
    Specification of an independent ground-truth validation scenario.

    Attributes
    ----------
    name : str
        Unique identifier for the test case.
    description : str
        Detailed explanation of the scenario and expected behavior.
    state : SystemState
        The instantiated system state under evaluation.
    expected_wfg_is_deadlocked : bool
        Expected boolean verdict for the Wait-For Graph detector.
    expected_wfg_deadlocked_processes : List[int]
        Expected cycle members in the WFG.
    expected_wfg_cycles : List[List[int]]
        Expected elementary cycles in the WFG.
    expected_wfg_blocked_processes : List[int]
        Expected processes blocked behind deadlocked cycles in the WFG.
    expected_multi_is_deadlocked : bool
        Expected boolean verdict for the Multi-Instance detector.
    expected_multi_deadlocked_processes : List[int]
        Expected un-finishable processes in the Multi-Instance detector.
    is_single_instance : bool
        Whether the resource model is single-instance.
    """
    name: str
    description: str
    state: SystemState
    expected_wfg_is_deadlocked: bool
    expected_wfg_deadlocked_processes: List[int]
    expected_wfg_cycles: List[List[int]]
    expected_wfg_blocked_processes: List[int]
    expected_multi_is_deadlocked: bool
    expected_multi_deadlocked_processes: List[int]
    is_single_instance: bool


def case_no_deadlock() -> GroundTruthCase:
    """Case 1: Linear chain of dependencies, terminating cleanly without cycles."""
    # P0 holds R0, requests R1 (held by P1)
    # P1 holds R1, has no outstanding requests
    state = SystemState(
        total=[1, 1],
        allocation=[
            [1, 0],
            [0, 1],
        ],
        request=[
            [0, 1],
            [0, 0],
        ],
        available=[0, 0],
    )
    return GroundTruthCase(
        name="no_deadlock",
        description="P0 holds R0 and requests R1; P1 holds R1 and has zero requests. P1 finishes, freeing R1 for P0.",
        state=state,
        expected_wfg_is_deadlocked=False,
        expected_wfg_deadlocked_processes=[],
        expected_wfg_cycles=[],
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=False,
        expected_multi_deadlocked_processes=[],
        is_single_instance=True,
    )


def case_one_deadlock_cycle() -> GroundTruthCase:
    """Case 2: Classic 2-process two-lock circular wait."""
    # P0 holds R0, requests R1 (held by P1)
    # P1 holds R1, requests R0 (held by P0)
    state = SystemState(
        total=[1, 1],
        allocation=[
            [1, 0],
            [0, 1],
        ],
        request=[
            [0, 1],
            [1, 0],
        ],
        available=[0, 0],
    )
    return GroundTruthCase(
        name="one_deadlock_cycle",
        description="P0 and P1 cross-hold and request each other's single-instance resources, forming cycle P0 <-> P1.",
        state=state,
        expected_wfg_is_deadlocked=True,
        expected_wfg_deadlocked_processes=[0, 1],
        expected_wfg_cycles=[[0, 1]],
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=True,
        expected_multi_deadlocked_processes=[0, 1],
        is_single_instance=True,
    )


def case_multiple_deadlock_cycles() -> GroundTruthCase:
    """Case 3: Two disjoint 2-process deadlock cycles in the same system."""
    # Cycle 1: P0 <-> P1 on R0, R1
    # Cycle 2: P2 <-> P3 on R2, R3
    state = SystemState(
        total=[1, 1, 1, 1],
        allocation=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
        request=[
            [0, 1, 0, 0],
            [1, 0, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 0],
        ],
        available=[0, 0, 0, 0],
    )
    return GroundTruthCase(
        name="multiple_deadlock_cycles",
        description="Two disjoint circular waits: (P0 <-> P1) on {R0, R1} and (P2 <-> P3) on {R2, R3}.",
        state=state,
        expected_wfg_is_deadlocked=True,
        expected_wfg_deadlocked_processes=[0, 1, 2, 3],
        expected_wfg_cycles=[[0, 1], [2, 3]],
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=True,
        expected_multi_deadlocked_processes=[0, 1, 2, 3],
        is_single_instance=True,
    )


def case_processes_blocked_behind_deadlock() -> GroundTruthCase:
    """Case 4: A deadlock cycle plus an innocent process waiting on a deadlocked process."""
    # Cycle: P0 <-> P1 on R0, R1
    # P2 holds R2, requests R0 (held by P0). P2 is NOT in the cycle, but blocked behind it.
    state = SystemState(
        total=[1, 1, 1],
        allocation=[
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ],
        request=[
            [0, 1, 0],
            [1, 0, 0],
            [1, 0, 0],
        ],
        available=[0, 0, 0],
    )
    return GroundTruthCase(
        name="processes_blocked_behind_deadlock",
        description="P0 and P1 form a cycle. P2 waits for P0. P2 is blocked behind the deadlock but is not in the cycle.",
        state=state,
        expected_wfg_is_deadlocked=True,
        expected_wfg_deadlocked_processes=[0, 1],
        expected_wfg_cycles=[[0, 1]],
        expected_wfg_blocked_processes=[2],
        expected_multi_is_deadlocked=True,
        expected_multi_deadlocked_processes=[0, 1, 2],  # Multi-instance detector marks all unfinishable as deadlocked
        is_single_instance=True,
    )


def case_multiple_resource_instances_safe() -> GroundTruthCase:
    """Case 5a: Canonical multi-instance resource system without deadlock (Silberschatz §8.6.2)."""
    # 5 processes, 3 resource types: Total = [7, 2, 6], Available = [0, 0, 0]
    # P0 and P2 have Request == 0, so they finish and release allocations, cascading to allow all to finish.
    state = SystemState(
        total=[7, 2, 6],
        allocation=[
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 3],
            [2, 1, 1],
            [0, 0, 2],
        ],
        request=[
            [0, 0, 0],
            [2, 0, 2],
            [0, 0, 0],
            [1, 0, 0],
            [0, 0, 2],
        ],
        available=[0, 0, 0],
    )
    return GroundTruthCase(
        name="multiple_resource_instances_safe",
        description="Silberschatz §8.6.2 canonical safe multi-instance scenario. All 5 processes finish sequentially.",
        state=state,
        expected_wfg_is_deadlocked=False,
        expected_wfg_deadlocked_processes=[],
        expected_wfg_cycles=[],
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=False,
        expected_multi_deadlocked_processes=[],
        is_single_instance=False,
    )


def case_multiple_resource_instances_deadlocked() -> GroundTruthCase:
    """Case 5b: Canonical multi-instance resource system with deadlock (Silberschatz §8.6.2)."""
    # Modified so P2 requests [0, 0, 1]. P0 finishes, but P1, P2, P3, P4 cannot proceed.
    state = SystemState(
        total=[7, 2, 6],
        allocation=[
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 3],
            [2, 1, 1],
            [0, 0, 2],
        ],
        request=[
            [0, 0, 0],
            [2, 0, 2],
            [0, 0, 1],
            [1, 0, 0],
            [0, 0, 2],
        ],
        available=[0, 0, 0],
    )
    return GroundTruthCase(
        name="multiple_resource_instances_deadlocked",
        description="Silberschatz §8.6.2 deadlocked multi-instance scenario. Processes P1, P2, P3, P4 are deadlocked.",
        state=state,
        expected_wfg_is_deadlocked=True,
        expected_wfg_deadlocked_processes=[1, 2, 3, 4],
        expected_wfg_cycles=[],  # Cycles in multi-instance do not map 1:1 to deadlocks
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=True,
        expected_multi_deadlocked_processes=[1, 2, 3, 4],
        is_single_instance=False,
    )


def case_zero_allocation() -> GroundTruthCase:
    """Case 6: Unallocated processes holding no resources initialized to Finish=True."""
    # P0 holds no resources (Allocation=[0, 0]), requests [1, 0]
    # P1 holds [1, 0], requests [0, 1]
    # P2 holds [0, 1], requests [0, 0]
    # Available = [1, 1]
    state = SystemState(
        total=[2, 2],
        allocation=[
            [0, 0],
            [1, 0],
            [0, 1],
        ],
        request=[
            [1, 0],
            [0, 1],
            [0, 0],
        ],
        available=[1, 1],
    )
    return GroundTruthCase(
        name="zero_allocation",
        description="P0 holds 0 resources and is marked Finish=True at Step 2; P2 and P1 finish sequentially.",
        state=state,
        expected_wfg_is_deadlocked=False,
        expected_wfg_deadlocked_processes=[],
        expected_wfg_cycles=[],
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=False,
        expected_multi_deadlocked_processes=[],
        is_single_instance=False,
    )


def case_available_resources_allow_finish() -> GroundTruthCase:
    """Case 7: Potential cycle broken because Available capacity satisfies requests."""
    # P0 and P1 cross-hold and request, BUT Available=[1, 1] satisfies P0 immediately!
    state = SystemState(
        total=[2, 2],
        allocation=[
            [1, 0],
            [0, 1],
        ],
        request=[
            [0, 1],
            [1, 0],
        ],
        available=[1, 1],
    )
    return GroundTruthCase(
        name="available_resources_allow_finish",
        description="Processes cross-request held resources, but Available headroom satisfies P0 immediately, preventing deadlock.",
        state=state,
        expected_wfg_is_deadlocked=False,
        expected_wfg_deadlocked_processes=[],
        expected_wfg_cycles=[],
        expected_wfg_blocked_processes=[],
        expected_multi_is_deadlocked=False,
        expected_multi_deadlocked_processes=[],
        is_single_instance=False,
    )


def get_all_ground_truth_cases() -> Dict[str, GroundTruthCase]:
    """Returns a dictionary of all standard ground-truth validation cases."""
    cases = [
        case_no_deadlock(),
        case_one_deadlock_cycle(),
        case_multiple_deadlock_cycles(),
        case_processes_blocked_behind_deadlock(),
        case_multiple_resource_instances_safe(),
        case_multiple_resource_instances_deadlocked(),
        case_zero_allocation(),
        case_available_resources_allow_finish(),
    ]
    return {c.name: c for c in cases}
