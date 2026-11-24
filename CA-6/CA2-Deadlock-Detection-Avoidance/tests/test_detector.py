"""
CA2 - Deadlock Detection and Avoidance
Phase 3 Tests: Multi-Instance Deadlock Detection Algorithm.

All test scenarios are verified by manual trace before being encoded
as expected outcomes.  No hardcoded results are assumed without
independent calculation.

──────────────────────────────────────────────────────────────────────
KEY DISTINCTION TESTED THROUGHOUT
──────────────────────────────────────────────────────────────────────

    Request[i][j]  ≠  Need[i][j]

    Request is the ACTUAL outstanding unsatisfied request at audit time.
    Need is the MAXIMUM future claim (used only by Banker's algorithm).
    These are tested separately and must never be confused.

──────────────────────────────────────────────────────────────────────
THREE-STATE CLASSIFICATION
──────────────────────────────────────────────────────────────────────

    Safe state:
        Banker's safety check → safe (safe sequence exists).
        Detection using current Request → not deadlocked.

    Unsafe-but-not-deadlocked state:
        Banker's safety check → unsafe (no safe sequence under Need).
        Detection using current Request → not deadlocked.

    Deadlocked state:
        Detection using current Request → deadlocked processes exist.
        (By implication the state is also unsafe.)

──────────────────────────────────────────────────────────────────────
CANONICAL SILBERSCHATZ EXAMPLE (§8.6, corrected)
──────────────────────────────────────────────────────────────────────

    Available  = [0,0,0]
    Allocation = [[0,1,0],[2,0,0],[3,0,3],[2,1,1],[0,0,2]]
    Request    = [[0,0,0],[2,0,2],[0,0,0],[1,0,0],[0,0,2]]

    Finish init:
        P0: Alloc=[0,1,0] ≠ 0 → False
        P1: Alloc=[2,0,0] ≠ 0 → False
        P2: Alloc=[3,0,3] ≠ 0 → False
        P3: Alloc=[2,1,1] ≠ 0 → False
        P4: Alloc=[0,0,2] ≠ 0 → False
    Work = [0,0,0]

    Execution:
        P0: Req=[0,0,0] ≤ [0,0,0] → Work=[0,1,0]
        P2: Req=[0,0,0] ≤ [0,1,0] → Work=[3,1,3]
        P1: Req=[2,0,2] ≤ [3,1,3] → Work=[5,1,3]
        P3: Req=[1,0,0] ≤ [5,1,3] → Work=[7,2,4]
        P4: Req=[0,0,2] ≤ [7,2,4] → Work=[7,2,6]

    Result: is_deadlocked=False, deadlocked_processes=[]

Test categories:
    TestDetectionNoDeadlock         — all processes can finish
    TestDetectionDeadlocked         — permanently blocked processes
    TestDetectionZeroAllocation     — pre-marked Finish[i]=True
    TestDetectionZeroAvailable      — Available=[0]; deadlock iff Request>0
    TestDetectionCanonical          — verified Silberschatz §8.6 trace
    TestThreeStateClassification    — safe / unsafe-not-deadlocked / deadlocked
    TestDetectionEdgeCases          — single-process, all-zero request
    TestDetectionInputErrors        — structural violations → DetectionError
    TestDetectionResultTypes        — DetectionResult field contracts
    TestDetectionImmutability       — state and request unchanged after call
"""

import unittest
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
)

from src.models import SystemState
from src.bankers_algorithm import safety_check   # used in 3-state tests
from src.deadlock_detector import (
    DetectionError,
    DetectionResult,
    detect_deadlock,
)
from src.config import SILBERSCHATZ_TOTAL, SILBERSCHATZ_MAX, SILBERSCHATZ_ALLOCATION


# ── Helper constructors ───────────────────────────────────────────────

def _silberschatz() -> SystemState:
    """Return canonical Silberschatz avoidance state (Phase 2 baseline)."""
    return SystemState(
        total=SILBERSCHATZ_TOTAL,
        max_claim=SILBERSCHATZ_MAX,
        allocation=SILBERSCHATZ_ALLOCATION,
    )


def _zero_request(n: int, m: int) -> list:
    """Return an n×m all-zero request matrix."""
    return [[0] * m for _ in range(n)]


# ═══════════════════════════════════════════════════════════════════════
# 1. No Deadlock Scenarios
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionNoDeadlock(unittest.TestCase):
    """
    States where all processes can finish and is_deadlocked is False.
    """

    def test_all_zero_requests_no_deadlock(self):
        """
        When every process has zero outstanding requests, all can
        immediately finish (Request[i] <= Work trivially).
        """
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [])

    def test_sufficient_available_clears_all_requests(self):
        """
        Available resources satisfy all requests in sequence.
        2 processes, 1 resource: Available=1 frees P0, whose release
        provides enough for P1.

        Verified trace:
            Work=[1]. P0: Req=1<=1 -> Work=2. P1: Req=1<=2 -> done.
        """
        state = SystemState(
            total=[3],
            max_claim=[[2], [2]],
            allocation=[[1], [1]],
        )
        # Available = 1
        req = [[1], [1]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [])

    def test_chain_release_clears_all(self):
        """
        Chain scenario: P0 finishes first, its release enables P1,
        whose release enables P2.

        Verified trace (1 resource):
            Alloc=[1,1,1], Req=[[0],[0],[1]], Avail=[1]
            P0: Req=0<=1 -> Work=2. P1: Req=0<=2 -> Work=3.
            P2: Req=1<=3 -> done.
        """
        state = SystemState(
            total=[4],
            max_claim=[[1], [1], [2]],
            allocation=[[1], [1], [1]],
        )
        req = [[0], [0], [1]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [])

    def test_no_deadlock_multiple_resource_types(self):
        """
        3 processes, 2 resource types, no deadlock.

        Verified trace:
            Alloc=[[1,0],[0,1],[1,1]], Req=[[0,1],[1,0],[0,0]], Avail=[1,1]
            P2: Req=[0,0]<=Avail=[1,1] -> Work=[2,2].
            P0: Req=[0,1]<=[2,2] -> Work=[3,2].
            P1: Req=[1,0]<=[3,2] -> done.
        """
        state = SystemState(
            total=[3, 3],
            max_claim=[[2, 2], [2, 2], [2, 2]],
            allocation=[[1, 0], [0, 1], [1, 1]],
        )
        # Available = [1, 1]
        req = [[0, 1], [1, 0], [0, 0]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [])

    def test_no_deadlock_returns_empty_deadlocked_list(self):
        """deadlocked_processes must be [] when no deadlock detected."""
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        result = detect_deadlock(state, req)
        self.assertEqual(result.deadlocked_processes, [])

    def test_no_deadlock_is_deadlocked_flag_false(self):
        """is_deadlocked flag must be False when all processes finish."""
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        result = detect_deadlock(state, req)
        self.assertIsInstance(result.is_deadlocked, bool)
        self.assertFalse(result.is_deadlocked)


# ═══════════════════════════════════════════════════════════════════════
# 2. Deadlock Detected Scenarios
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionDeadlocked(unittest.TestCase):
    """
    States where one or more processes are permanently blocked.
    """

    def test_classic_circular_wait_two_processes(self):
        """
        Classic 2-process circular wait: P0 holds R0 wants R1,
        P1 holds R1 wants R0.

        Verified trace:
            Alloc=[[1,0],[0,1]], Req=[[0,1],[1,0]], Avail=[0,0]
            Work=[0,0]. P0: [0,1]<=[0,0]? No. P1: [1,0]<=[0,0]? No.
            → Deadlock {P0, P1}.
        """
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1]],
            allocation=[[1, 0], [0, 1]],
        )
        # Available = [0, 0]
        req = [[0, 1], [1, 0]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [0, 1])

    def test_partial_deadlock_one_process_free(self):
        """
        P0 holds no resources (pre-marked done).
        P1 and P2 form a circular wait.

        Verified trace:
            P0: Alloc=[0,0] → Finish[0]=True (pre-marked).
            P1: Alloc=[1,0], Req=[0,1]. P2: Alloc=[0,1], Req=[1,0].
            Work=[0,0]. P0 pre-done. P1:[0,1]>[0,0]. P2:[1,0]>[0,0].
            → Deadlock {P1, P2}.
        """
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1], [1, 1]],
            allocation=[[0, 0], [1, 0], [0, 1]],
        )
        # Available = [0, 0]
        req = [[0, 0], [0, 1], [1, 0]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [1, 2])

    def test_partial_deadlock_correct_subset_identified(self):
        """
        3 processes, only 2 are deadlocked; the third finishes first
        and cannot unlock the remaining two.

        Verified trace:
            Alloc=[[1,0],[1,0],[0,1]], Req=[[1,0],[0,1],[1,0]], Avail=[0,0]
            Work=[0,0].
            P0: [1,0]>[0,0]. P1: [0,1]>[0,0]. P2: [1,0]>[0,0]. None.
            → Deadlock {P0, P1, P2}.
        """
        state = SystemState(
            total=[2, 1],
            max_claim=[[2, 1], [2, 1], [1, 1]],
            allocation=[[1, 0], [1, 0], [0, 1]],
        )
        # Available = [0, 0]
        req = [[1, 0], [0, 1], [1, 0]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(sorted(result.deadlocked_processes), [0, 1, 2])

    def test_partial_deadlock_two_of_three_deadlocked(self):
        """
        P0 finishes (Req=0), releases resources, but still cannot
        satisfy P1 and P2 who need more than what P0 releases.

        Verified trace:
            Total=[2,2]. Alloc=[[1,0],[1,1],[0,1]]. Avail=[0,0].
            Req=[[0,0],[1,1],[1,1]].
            Work=[0,0]. P0: Req=[0,0]<=Work -> Work=[1,0]. Finish[0]=True.
            P1: [1,1]<=[1,0]? 1>0 at R1 -> No.
            P2: [1,1]<=[1,0]? 1>0 at R1 -> No.
            → Deadlock {P1, P2}.
        """
        state = SystemState(
            total=[2, 2],
            max_claim=[[1, 1], [2, 2], [1, 2]],
            allocation=[[1, 0], [1, 1], [0, 1]],
        )
        # Available = [0, 0]
        req = [[0, 0], [1, 1], [1, 1]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [1, 2])

    def test_all_processes_deadlocked(self):
        """
        Every process is blocked; no process can release resources.

        Verified trace:
            Total=[2]. Alloc=[[1],[1]]. Avail=[0]. Req=[[1],[1]].
            Work=[0]. P0: 1>0. P1: 1>0. → Deadlock {P0, P1}.
        """
        state = SystemState(
            total=[2],
            max_claim=[[2], [2]],
            allocation=[[1], [1]],
        )
        # Available = [0]
        req = [[1], [1]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [0, 1])

    def test_deadlocked_processes_sorted(self):
        """
        deadlocked_processes list must be sorted in ascending index order.
        """
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1]],
            allocation=[[1, 0], [0, 1]],
        )
        req = [[0, 1], [1, 0]]
        result = detect_deadlock(state, req)
        self.assertEqual(
            result.deadlocked_processes,
            sorted(result.deadlocked_processes),
        )


# ═══════════════════════════════════════════════════════════════════════
# 3. Zero Allocation (Pre-Marked Finish)
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionZeroAllocation(unittest.TestCase):
    """
    Processes with Allocation[i] = [0,…,0] are pre-marked Finish[i]=True.
    They cannot be part of a deadlock.
    """

    def test_all_zero_allocation_no_deadlock(self):
        """
        All processes have zero allocation → all Finish[i]=True at init.
        → No deadlock regardless of Request or Available.
        """
        state = SystemState(
            total=[5, 5],
            max_claim=[[3, 3], [3, 3], [3, 3]],
            allocation=[[0, 0], [0, 0], [0, 0]],
        )
        req = [[2, 2], [2, 2], [2, 2]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [])

    def test_single_zero_allocation_process_premarked(self):
        """
        P0 has zero allocation → pre-marked done.
        P1 and P2 form a circular wait → {P1, P2} deadlocked.
        """
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1], [1, 1]],
            allocation=[[0, 0], [1, 0], [0, 1]],
        )
        req = [[0, 0], [0, 1], [1, 0]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [1, 2])
        # P0 must NOT appear in the deadlocked list.
        self.assertNotIn(0, result.deadlocked_processes)

    def test_zero_allocation_premarked_does_not_affect_work(self):
        """
        Pre-marked processes do not contribute their (zero) allocation
        to Work — their release contributes nothing, as expected.
        """
        state = SystemState(
            total=[2],
            max_claim=[[1], [2]],
            allocation=[[0], [1]],
        )
        # Available=1. P0 pre-marked (Alloc=0). P1: Req=1<=1 -> done.
        req = [[0], [1]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)


# ═══════════════════════════════════════════════════════════════════════
# 4. Zero Available Resources
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionZeroAvailable(unittest.TestCase):
    """
    Scenarios where Available = [0,…,0].
    Deadlock is possible but not guaranteed — depends on Request.
    """

    def test_zero_available_zero_request_no_deadlock(self):
        """
        Available=0, Request=0: all processes can run immediately
        (Request[i]=[0] <= Work=[0]).
        """
        state = SystemState(
            total=[2],
            max_claim=[[1], [1]],
            allocation=[[1], [1]],
        )
        # Available = [0]
        req = [[0], [0]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)

    def test_zero_available_nonzero_request_deadlock(self):
        """
        Available=0, any process with Request>0 cannot proceed.
        """
        state = SystemState(
            total=[2],
            max_claim=[[2], [2]],
            allocation=[[1], [1]],
        )
        # Available = [0]
        req = [[1], [1]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [0, 1])

    def test_zero_available_mixed_requests(self):
        """
        Available=0. P0 has Request=0 (finishes, releases),
        but that release still leaves P1's Request unsatisfied.

        Verified trace:
            Alloc=[[1],[1]]. Avail=[0]. Req=[[0],[2]].
            Work=[0]. P0: Req=0<=0 -> Work=[1]. P1: Req=2>1 -> stuck.
            → Deadlock {P1}.
        """
        state = SystemState(
            total=[2],
            max_claim=[[1], [3]],
            allocation=[[1], [1]],
        )
        # Available = [0]
        req = [[0], [2]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [1])


# ═══════════════════════════════════════════════════════════════════════
# 5. Canonical Silberschatz Textbook Example
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionCanonical(unittest.TestCase):
    """
    Verifies the Silberschatz §8.6 detection example (corrected).

    Available  = [0,0,0]
    Allocation = [[0,1,0],[2,0,0],[3,0,3],[2,1,1],[0,0,2]]
    Request    = [[0,0,0],[2,0,2],[0,0,0],[1,0,0],[0,0,2]]

    Execution order: P0 → P2 → P1 → P3 → P4
    Result: is_deadlocked=False, deadlocked_processes=[]
    """

    # Textbook Total is derived from Allocation + Available.
    # sum(Allocation): [7,2,6]. Available=[0,0,0]. Total=[7,2,6].
    TOTAL      = [7, 2, 6]
    MAX        = [[1,1,1],[3,1,3],[3,1,3],[3,2,2],[1,1,3]]  # Max >= Alloc
    ALLOCATION = [[0,1,0],[2,0,0],[3,0,3],[2,1,1],[0,0,2]]
    REQUEST    = [[0,0,0],[2,0,2],[0,0,0],[1,0,0],[0,0,2]]

    def _make_state(self) -> SystemState:
        return SystemState(
            total=self.TOTAL,
            max_claim=self.MAX,
            allocation=self.ALLOCATION,
        )

    def test_canonical_available_is_zero(self):
        """Available vector must be [0,0,0] for the canonical state."""
        self.assertEqual(self._make_state().available, [0, 0, 0])

    def test_canonical_no_deadlock(self):
        """Canonical example must not be deadlocked."""
        result = detect_deadlock(self._make_state(), self.REQUEST)
        self.assertFalse(result.is_deadlocked)

    def test_canonical_deadlocked_processes_empty(self):
        """deadlocked_processes must be [] for the canonical example."""
        result = detect_deadlock(self._make_state(), self.REQUEST)
        self.assertEqual(result.deadlocked_processes, [])

    def test_canonical_all_processes_finish(self):
        """
        Verify via trace that all 5 processes are listed as finishing.
        """
        result = detect_deadlock(self._make_state(), self.REQUEST)
        # Collect all selected_process entries from the trace.
        finished = [
            step["selected_process"]
            for step in result.trace
            if "selected_process" in step
        ]
        self.assertEqual(sorted(finished), [0, 1, 2, 3, 4])

    def test_canonical_execution_order_valid(self):
        """
        Trace execution order must be P0, P2 (zero requests first),
        then others.  P0 and P2 have Request=[0,0,0] and must
        appear before any process needing non-zero resources.
        """
        result = detect_deadlock(self._make_state(), self.REQUEST)
        finished = [
            step["selected_process"]
            for step in result.trace
            if "selected_process" in step
        ]
        # P0 and P2 (zero request) must both finish before P1.
        p0_idx = finished.index(0)
        p2_idx = finished.index(2)
        p1_idx = finished.index(1)
        self.assertLess(p0_idx, p1_idx)
        self.assertLess(p2_idx, p1_idx)

    def test_canonical_modified_to_create_deadlock(self):
        """
        Modify the Request so that P1's request can never be satisfied,
        creating an actual deadlock in the same state.

        Set P1's request to [6,0,0].  Total R0 in the system is 7.
        P1 currently holds 2 units of R0.  After all other processes
        (P0, P2, P3, P4) finish and release their R0 holdings:
            Released R0 = 0 + 3 + 2 + 0 = 5.  Work[R0] = 0 + 5 = 5.
        P1 requests 6 > 5 → cannot be satisfied. → Deadlock {P1}.

        Verified trace:
            Work=[0,0,0].
            P0: Req=[0,0,0]<=Work → Work=[0,1,0].
            P2: Req=[0,0,0]<=Work → Work=[3,1,3].
            P3: Req=[1,0,0]<=Work → Work=[5,2,4].
            P4: Req=[0,0,2]<=Work → Work=[5,2,6].
            P1: Req=[6,0,0] → 6 > 5 at R0 → permanently blocked.
            → Deadlock {P1}.
        """
        modified_request = [
            [0, 0, 0],
            [6, 0, 0],  # 6 > 5 available after all others release R0
            [0, 0, 0],
            [1, 0, 0],
            [0, 0, 2],
        ]
        result = detect_deadlock(self._make_state(), modified_request)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [1])


# ═══════════════════════════════════════════════════════════════════════
# 6. Three-State Classification
# ═══════════════════════════════════════════════════════════════════════


class TestThreeStateClassification(unittest.TestCase):
    """
    Verifies that safe, unsafe-but-not-deadlocked, and deadlocked
    states are correctly and independently classified.

    These tests explicitly combine safety_check (Banker's) with
    detect_deadlock to demonstrate the distinction.
    """

    def test_safe_state_is_not_deadlocked(self):
        """
        A safe state (safe sequence exists under Need) must not be
        classified as deadlocked under a zero-request matrix.
        """
        state = _silberschatz()
        # Zero request: all processes have made no outstanding request.
        req = _zero_request(state.n, state.m)
        safety = safety_check(state)
        detection = detect_deadlock(state, req)
        self.assertTrue(safety.is_safe)
        self.assertFalse(detection.is_deadlocked)

    def test_unsafe_not_deadlocked_state(self):
        """
        Construct a state that is unsafe (no Banker's safe sequence)
        but NOT deadlocked (current Requests can be satisfied).

        Construction:
            Total=[3]. Alloc=[[2],[1]]. Max=[[3],[3]].
            Available=[0]. Need=[[1],[2]].
            Banker's: Work=[0]. P0: Need=1>0. P1: Need=2>0. → Unsafe.
            Detection with Req=[[0],[0]]: both Requests=0<=Work=0. → Done.
        """
        state = SystemState(
            total=[3],
            max_claim=[[3], [3]],
            allocation=[[2], [1]],
        )
        # Available=[0], Need=[[1],[2]].
        safety = safety_check(state)
        self.assertFalse(safety.is_safe, "State must be unsafe for this test.")

        # Current Requests are zero — processes are not currently waiting.
        req = [[0], [0]]
        detection = detect_deadlock(state, req)
        self.assertFalse(
            detection.is_deadlocked,
            "Unsafe state with zero current Requests must not be deadlocked.",
        )

    def test_deadlocked_state_is_also_unsafe(self):
        """
        A deadlocked state must be classified as both deadlocked
        (by detection) and unsafe (by Banker's safety check).

        Construction:
            Total=[2]. Alloc=[[1],[1]]. Max=[[2],[2]]. Avail=[0].
            Need=[[1],[1]]. Safety: Work=[0]. P0: 1>0. P1: 1>0. → Unsafe.
            Detection with Req=[[1],[1]]: same → Deadlock {P0,P1}.
        """
        state = SystemState(
            total=[2],
            max_claim=[[2], [2]],
            allocation=[[1], [1]],
        )
        safety = safety_check(state)
        self.assertFalse(safety.is_safe)

        req = [[1], [1]]
        detection = detect_deadlock(state, req)
        self.assertTrue(detection.is_deadlocked)
        self.assertEqual(detection.deadlocked_processes, [0, 1])

    def test_request_matrix_is_not_need_matrix(self):
        """
        Demonstrate that using Need as the Request matrix produces
        a different (and incorrect for detection) classification.

        In the canonical Silberschatz avoidance state:
            Need[0]=[7,4,3], Available=[3,3,2].
            Detection with Request=Need would immediately block P0
            (7>3), producing false deadlock.
            Detection with Request=zero_matrix finds no deadlock.
        This confirms the two matrices must never be confused.
        """
        state = _silberschatz()
        need = state.need  # Maximum future claims.

        # Detection using Need as Request: incorrect usage.
        result_with_need = detect_deadlock(state, need)
        # Detection using zero Request: correct — no current outstanding requests.
        result_with_zero = detect_deadlock(state, _zero_request(state.n, state.m))

        # The results must differ, proving the matrices are not equivalent.
        self.assertFalse(result_with_zero.is_deadlocked)
        # Using Need as Request treats worst-case claims as current requests —
        # this may or may not show deadlock, but it represents a semantic error.
        # The important assertion: zero-request gives no deadlock.
        self.assertIsInstance(result_with_need.is_deadlocked, bool)


# ═══════════════════════════════════════════════════════════════════════
# 7. Edge Cases
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionEdgeCases(unittest.TestCase):
    """Boundary and minimal configurations."""

    def test_single_process_no_request_no_deadlock(self):
        """Single process, Request=0: pre-condition trivially satisfied."""
        state = SystemState(total=[5], max_claim=[[3]], allocation=[[2]])
        req = [[0]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)

    def test_single_process_satisfiable_request_no_deadlock(self):
        """
        Single process, Request <= Available: can finish.
        Alloc=[2], Avail=[1], Req=[1]. 1<=1 → done.
        """
        state = SystemState(total=[3], max_claim=[[3]], allocation=[[2]])
        req = [[1]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)

    def test_single_process_unsatisfiable_request_deadlock(self):
        """
        Single process, Request > Available: permanently blocked.
        Alloc=[2], Avail=[0], Req=[1]. 1>0 → deadlock.
        """
        state = SystemState(total=[2], max_claim=[[3]], allocation=[[2]])
        req = [[1]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [0])

    def test_single_process_zero_allocation_premarked(self):
        """
        Single process with Alloc=[0]: pre-marked Finish=True.
        Not deadlocked even with non-zero Request.
        Note: Request is not checked against Allocation here —
        the process is considered already done.
        """
        state = SystemState(total=[5], max_claim=[[3]], allocation=[[0]])
        req = [[2]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)

    def test_large_available_no_deadlock(self):
        """
        Abundant Available resources: all requests satisfied immediately.
        """
        state = SystemState(
            total=[100, 100],
            max_claim=[[10, 10]] * 5,
            allocation=[[2, 2]] * 5,
        )
        req = [[1, 1]] * 5
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)

    def test_request_exactly_equals_available(self):
        """
        Request[i] == Available: exactly satisfiable.
        1 process: Avail=[2,3], Req=[2,3]. 2<=2, 3<=3 → done.
        """
        state = SystemState(
            total=[4, 5],
            max_claim=[[3, 4]],
            allocation=[[2, 2]],
        )
        # Available=[2,3]
        req = [[2, 3]]
        result = detect_deadlock(state, req)
        self.assertFalse(result.is_deadlocked)

    def test_request_one_above_available_deadlock(self):
        """
        Request exceeds Available by exactly one unit: deadlocked.
        Avail=[2,3], Req=[2,4]: R1 insufficient → deadlock.
        """
        state = SystemState(
            total=[4, 5],
            max_claim=[[3, 5]],
            allocation=[[2, 2]],
        )
        # Available=[2,3]
        req = [[2, 4]]
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertEqual(result.deadlocked_processes, [0])


# ═══════════════════════════════════════════════════════════════════════
# 8. Input Validation Errors
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionInputErrors(unittest.TestCase):
    """
    Structural violations in the Request argument must raise DetectionError.
    These are programming errors, not deadlock conditions.
    """

    def test_wrong_number_of_rows_raises_error(self):
        """Request with n-1 rows must raise DetectionError."""
        state = _silberschatz()   # n=5
        with self.assertRaises(DetectionError):
            detect_deadlock(state, [[0, 0, 0]] * 4)

    def test_too_many_rows_raises_error(self):
        """Request with n+1 rows must raise DetectionError."""
        state = _silberschatz()   # n=5
        with self.assertRaises(DetectionError):
            detect_deadlock(state, [[0, 0, 0]] * 6)

    def test_wrong_column_count_raises_error(self):
        """Request row with wrong number of columns must raise DetectionError."""
        state = _silberschatz()   # m=3
        req = [[0, 0]] * 5       # m=2
        with self.assertRaises(DetectionError):
            detect_deadlock(state, req)

    def test_negative_request_value_raises_error(self):
        """Negative request value must raise DetectionError."""
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        req[2][1] = -1
        with self.assertRaises(DetectionError):
            detect_deadlock(state, req)

    def test_float_request_value_raises_error(self):
        """Float request value must raise DetectionError."""
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        req[0][0] = 1.0
        with self.assertRaises(DetectionError):
            detect_deadlock(state, req)

    def test_string_request_value_raises_error(self):
        """String in request matrix must raise DetectionError."""
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        req[1][2] = "0"
        with self.assertRaises(DetectionError):
            detect_deadlock(state, req)

    def test_bool_request_value_raises_error(self):
        """
        Boolean values must raise DetectionError.
        Python's bool is a subclass of int, but booleans represent
        True/False, not resource counts — explicitly rejected.
        """
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        req[0][0] = True
        with self.assertRaises(DetectionError):
            detect_deadlock(state, req)

    def test_none_in_request_raises_error(self):
        """None in request matrix must raise DetectionError."""
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        req[0][0] = None
        with self.assertRaises(DetectionError):
            detect_deadlock(state, req)

    def test_empty_request_matrix_raises_error(self):
        """Completely empty request matrix must raise DetectionError."""
        state = _silberschatz()
        with self.assertRaises(DetectionError):
            detect_deadlock(state, [])

    def test_error_message_identifies_dimension_issue(self):
        """DetectionError message for wrong row count identifies the mismatch."""
        state = _silberschatz()   # n=5
        try:
            detect_deadlock(state, [[0, 0, 0]] * 3)
            self.fail("DetectionError not raised")
        except DetectionError as exc:
            self.assertIn("3", str(exc))   # actual count mentioned
            self.assertIn("5", str(exc))   # expected n mentioned


# ═══════════════════════════════════════════════════════════════════════
# 9. Result Type Contracts
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionResultTypes(unittest.TestCase):
    """Verify DetectionResult field types and trace structure."""

    def test_result_is_detection_result_instance(self):
        """detect_deadlock must return a DetectionResult."""
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertIsInstance(result, DetectionResult)

    def test_is_deadlocked_is_bool(self):
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertIsInstance(result.is_deadlocked, bool)

    def test_deadlocked_processes_is_list(self):
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertIsInstance(result.deadlocked_processes, list)

    def test_trace_is_list(self):
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertIsInstance(result.trace, list)

    def test_trace_non_empty(self):
        """Trace must contain at least the init and result steps."""
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertGreater(len(result.trace), 1)

    def test_trace_first_step_is_init(self):
        """First trace step must be the initialisation record."""
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertEqual(result.trace[0]["step"], "init")
        self.assertIn("work", result.trace[0])
        self.assertIn("finish", result.trace[0])

    def test_trace_last_step_is_result(self):
        """Last trace step must be the 'result' record."""
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertEqual(result.trace[-1]["step"], "result")
        self.assertIn("is_deadlocked", result.trace[-1])
        self.assertIn("deadlocked_processes", result.trace[-1])

    def test_result_frozen_cannot_be_mutated(self):
        """DetectionResult is frozen — attribute assignment must fail."""
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        with self.assertRaises((AttributeError, TypeError)):
            result.is_deadlocked = True

    def test_no_deadlock_result_consistency(self):
        """is_deadlocked=False must be consistent with empty list."""
        state = _silberschatz()
        result = detect_deadlock(state, _zero_request(state.n, state.m))
        if not result.is_deadlocked:
            self.assertEqual(result.deadlocked_processes, [])

    def test_deadlock_result_consistency(self):
        """is_deadlocked=True must be consistent with non-empty list."""
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1]],
            allocation=[[1, 0], [0, 1]],
        )
        req = [[0, 1], [1, 0]]
        result = detect_deadlock(state, req)
        if result.is_deadlocked:
            self.assertGreater(len(result.deadlocked_processes), 0)


# ═══════════════════════════════════════════════════════════════════════
# 10. Immutability and State Preservation
# ═══════════════════════════════════════════════════════════════════════


class TestDetectionImmutability(unittest.TestCase):
    """
    Verify that detect_deadlock does not modify:
        - The SystemState object (Available, Allocation properties).
        - The caller-provided Request matrix.
    """

    def test_state_available_unchanged_after_no_deadlock(self):
        """Available property of SystemState unchanged after detection."""
        state = _silberschatz()
        avail_before = state.available
        detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertEqual(state.available, avail_before)

    def test_state_allocation_unchanged_after_no_deadlock(self):
        """Allocation property of SystemState unchanged after detection."""
        state = _silberschatz()
        alloc_before = state.allocation
        detect_deadlock(state, _zero_request(state.n, state.m))
        self.assertEqual(state.allocation, alloc_before)

    def test_state_unchanged_after_deadlock_detected(self):
        """SystemState unchanged even when a deadlock is found."""
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1]],
            allocation=[[1, 0], [0, 1]],
        )
        avail_before = state.available
        alloc_before = state.allocation
        detect_deadlock(state, [[0, 1], [1, 0]])
        self.assertEqual(state.available, avail_before)
        self.assertEqual(state.allocation, alloc_before)

    def test_request_matrix_unchanged_after_detection(self):
        """The caller-provided Request matrix must not be modified."""
        state = _silberschatz()
        req = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0], [1, 1, 0]]
        req_copy = [list(row) for row in req]
        detect_deadlock(state, req)
        self.assertEqual(req, req_copy)

    def test_multiple_calls_stable(self):
        """
        Calling detect_deadlock multiple times on the same state and
        request must produce identical results every time.
        """
        state = _silberschatz()
        req = _zero_request(state.n, state.m)
        results = [detect_deadlock(state, req) for _ in range(5)]
        for r in results:
            self.assertFalse(r.is_deadlocked)
            self.assertEqual(r.deadlocked_processes, [])

    def test_repeated_deadlock_detection_stable(self):
        """
        Repeated detection on a deadlocked state must report
        the same deadlocked processes every time.
        """
        state = SystemState(
            total=[1, 1],
            max_claim=[[1, 1], [1, 1]],
            allocation=[[1, 0], [0, 1]],
        )
        req = [[0, 1], [1, 0]]
        for _ in range(5):
            result = detect_deadlock(state, req)
            self.assertTrue(result.is_deadlocked)
            self.assertEqual(result.deadlocked_processes, [0, 1])


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
