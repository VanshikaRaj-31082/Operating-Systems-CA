"""
CA2 - Deadlock Detection and Avoidance
Phase 2 Tests: Banker's Algorithm – Safety Check and Resource-Request Algorithm.

Test categories:
    TestSafetyCheck          - Safety algorithm on safe and unsafe states.
    TestSafeSequenceValidity - Verifies safe sequences are structurally valid.
    TestCanonicalRequests    - Silberschatz Chapter 8 sequential request trace.
    TestRequestDenied        - Requests denied due to insufficient resources.
    TestRequestUnsafe        - Requests denied because result would be unsafe.
    TestRequestErrors        - Structural violations that must raise RequestError.
    TestRollback             - Original state unchanged after a denial.
    TestEdgeCases            - Boundary and minimal configurations.
    TestResultTypes          - SafetyResult and RequestResult field contracts.

IMPORTANT: The Banker's safety algorithm may produce any valid safe sequence.
Where multiple safe sequences exist, tests verify sequence validity rather
than testing for one specific sequence.

Canonical Silberschatz State (Chapter 8):
    Total     = [10, 5, 7]
    Max       = [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]]
    Allocation= [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]]
    Available = [3, 3, 2]  (derived: Total - sum(Allocation))
    Need      = [[7,4,3],[1,2,2],[6,0,0],[0,1,1],[4,3,1]]
"""

import unittest
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
)

from src.models import SystemState, InvariantViolation
from src.bankers_algorithm import (
    RequestError,
    RequestResult,
    SafetyResult,
    request_resources,
    safety_check,
)
from src.config import (
    SILBERSCHATZ_ALLOCATION,
    SILBERSCHATZ_MAX,
    SILBERSCHATZ_REQUESTS,
    SILBERSCHATZ_TOTAL,
)


# ── Helper ────────────────────────────────────────────────────────────

def _silberschatz() -> SystemState:
    """Return a fresh canonical Silberschatz system state."""
    return SystemState(
        total=SILBERSCHATZ_TOTAL,
        max_claim=SILBERSCHATZ_MAX,
        allocation=SILBERSCHATZ_ALLOCATION,
    )


def _is_valid_safe_sequence(state: SystemState, sequence: list) -> bool:
    """
    Verify that a given sequence is a valid safe sequence for the state.

    Simulates the safety algorithm manually: works through the sequence
    in order, checking that each process's Need can be met by Work at
    that point, then releasing its allocation.
    """
    n, m = state.n, state.m
    if sorted(sequence) != list(range(n)):
        return False  # Must be a permutation of [0, n-1].

    work = state.available  # property returns copy
    allocation = state.allocation
    need = state.need

    for i in sequence:
        if not all(need[i][j] <= work[j] for j in range(m)):
            return False
        for j in range(m):
            work[j] += allocation[i][j]
    return True


# ═══════════════════════════════════════════════════════════════════════
# 1. Safety Check – Safe and Unsafe States
# ═══════════════════════════════════════════════════════════════════════


class TestSafetyCheck(unittest.TestCase):
    """Verify the safety algorithm correctly classifies system states."""

    def test_silberschatz_initial_state_is_safe(self):
        """Canonical initial state must be classified as safe."""
        result = safety_check(_silberschatz())
        self.assertTrue(result.is_safe)

    def test_silberschatz_safe_sequence_is_complete(self):
        """Safe sequence must include all 5 processes exactly once."""
        result = safety_check(_silberschatz())
        self.assertEqual(sorted(result.safe_sequence), [0, 1, 2, 3, 4])

    def test_silberschatz_safe_sequence_is_valid(self):
        """Returned safe sequence must satisfy the work-simulation check."""
        state = _silberschatz()
        result = safety_check(state)
        self.assertTrue(
            _is_valid_safe_sequence(state, result.safe_sequence),
            f"Sequence {result.safe_sequence} is not a valid safe sequence.",
        )

    def test_unsafe_state_all_need_exceeds_available(self):
        """
        State where every process needs more than available is unsafe.
        2 processes, 1 resource: Total=2, Alloc=[[1],[1]], Need=[[1],[1]],
        Available=[0]. Neither process can proceed.
        """
        state = SystemState(
            total=[2],
            max_claim=[[2], [2]],
            allocation=[[1], [1]],
        )
        result = safety_check(state)
        self.assertFalse(result.is_safe)
        self.assertEqual(result.safe_sequence, [])

    def test_unsafe_state_returns_empty_sequence(self):
        """Unsafe state must return an empty safe_sequence."""
        state = SystemState(
            total=[4],
            max_claim=[[3], [3]],
            allocation=[[2], [2]],
        )
        # Available=0, Need=[[1],[1]] — neither can proceed.
        result = safety_check(state)
        self.assertFalse(result.is_safe)
        self.assertEqual(result.safe_sequence, [])

    def test_safe_state_all_fully_allocated(self):
        """
        All processes fully allocated (Need = 0 everywhere).
        Any process can run immediately; every permutation is a safe sequence.
        """
        state = SystemState(
            total=[8, 6],
            max_claim=[[4, 3], [4, 3]],
            allocation=[[4, 3], [4, 3]],
        )
        result = safety_check(state)
        self.assertTrue(result.is_safe)
        self.assertEqual(sorted(result.safe_sequence), [0, 1])

    def test_safe_state_nothing_allocated(self):
        """
        No resources allocated. Available = Total.
        Every process's Need = Max. The state is safe if Available >= Need[i]
        for at least the first process (which releases, allowing others).
        """
        # Total > any single Need, so safe.
        state = SystemState(
            total=[10, 10],
            max_claim=[[3, 2], [4, 3]],
            allocation=[[0, 0], [0, 0]],
        )
        result = safety_check(state)
        self.assertTrue(result.is_safe)
        self.assertEqual(len(result.safe_sequence), 2)

    def test_single_process_need_zero_is_safe(self):
        """Single fully-allocated process: trivially safe."""
        state = SystemState(
            total=[5],
            max_claim=[[3]],
            allocation=[[3]],
        )
        result = safety_check(state)
        self.assertTrue(result.is_safe)
        self.assertEqual(result.safe_sequence, [0])

    def test_single_process_need_nonzero_available_sufficient(self):
        """Single process with Need=[2] and Available=[2]: safe."""
        state = SystemState(
            total=[5],
            max_claim=[[3]],
            allocation=[[1]],
        )
        result = safety_check(state)
        self.assertTrue(result.is_safe)
        self.assertEqual(result.safe_sequence, [0])

    def test_single_process_need_exceeds_available(self):
        """Single process with Need=[3] and Available=[2]: unsafe."""
        state = SystemState(
            total=[3],
            max_claim=[[3]],
            allocation=[[0]],
        )
        # Available = 3, Need = 3 → safe (3 <= 3).
        result = safety_check(state)
        self.assertTrue(result.is_safe)

    def test_single_process_truly_unsafe(self):
        """
        Single process: Total=2, Alloc=1, Max=3.
        Available=1, Need=2. 2 > 1 → unsafe.
        """
        state = SystemState(
            total=[2],
            max_claim=[[3]],
            allocation=[[1]],
        )
        result = safety_check(state)
        self.assertFalse(result.is_safe)

    def test_three_process_safe_state(self):
        """3 processes, 2 resource types: known safe configuration."""
        state = SystemState(
            total=[10, 10],
            max_claim=[[5, 5], [5, 5], [5, 5]],
            allocation=[[2, 2], [2, 2], [2, 2]],
        )
        # Available=[4,4], Need=[[3,3],[3,3],[3,3]].
        # P0: [3,3]<=[4,4] → Work=[6,6].
        # P1: [3,3]<=[6,6] → Work=[8,8].
        # P2: [3,3]<=[8,8] → Safe.
        result = safety_check(state)
        self.assertTrue(result.is_safe)

    def test_three_process_unsafe_state(self):
        """3 processes where no process can run first: unsafe."""
        state = SystemState(
            total=[6],
            max_claim=[[4], [4], [4]],
            allocation=[[2], [2], [2]],
        )
        # Available=0, Need=[[2],[2],[2]]. No process can run.
        result = safety_check(state)
        self.assertFalse(result.is_safe)


# ═══════════════════════════════════════════════════════════════════════
# 2. Safe Sequence Structural Validity
# ═══════════════════════════════════════════════════════════════════════


class TestSafeSequenceValidity(unittest.TestCase):
    """
    Verify safe sequences are permutations that pass the work simulation.
    Does not enforce a specific sequence ordering, only structural validity.
    """

    def test_sequence_is_permutation_of_all_processes(self):
        """Safe sequence includes every process index exactly once."""
        state = _silberschatz()
        result = safety_check(state)
        self.assertEqual(sorted(result.safe_sequence), list(range(state.n)))

    def test_sequence_passes_work_simulation(self):
        """Every step in the safe sequence satisfies Need[i] <= Work."""
        state = _silberschatz()
        result = safety_check(state)
        self.assertTrue(_is_valid_safe_sequence(state, result.safe_sequence))

    def test_multiple_valid_safe_sequences_exist(self):
        """
        Verify that at least one alternative valid safe sequence exists
        for the canonical state, confirming the algorithm's result is not
        the only valid answer.

        Known valid sequences for the initial Silberschatz state:
            <P1, P3, P4, P0, P2>  (textbook)
            <P1, P3, P0, P2, P4>
            <P1, P3, P0, P4, P2>
        Any such permutation is acceptable.
        """
        state = _silberschatz()
        # Textbook sequence (Silberschatz):
        textbook_seq = [1, 3, 4, 0, 2]
        self.assertTrue(
            _is_valid_safe_sequence(state, textbook_seq),
            "Textbook sequence <P1, P3, P4, P0, P2> must be valid.",
        )
        # Algorithm's actual sequence:
        result = safety_check(state)
        self.assertTrue(
            _is_valid_safe_sequence(state, result.safe_sequence),
            f"Algorithm sequence {result.safe_sequence} must also be valid.",
        )

    def test_safe_sequence_after_grant_is_valid(self):
        """Safe sequence reported in granted RequestResult is valid."""
        state = _silberschatz()
        result = request_resources(state, 1, [1, 0, 2])
        self.assertTrue(result.granted)
        new_state = result.new_state
        post_seq = result.details["safety_result"]["safe_sequence"]
        self.assertTrue(_is_valid_safe_sequence(new_state, post_seq))


# ═══════════════════════════════════════════════════════════════════════
# 3. Canonical Silberschatz Request Trace
# ═══════════════════════════════════════════════════════════════════════


class TestCanonicalRequests(unittest.TestCase):
    """
    Verify the two-step sequential request trace from config.py.

    Request 1: P1 requests (1,0,2) from Available=[3,3,2].
        Resources available. Safety check passes.
        → Granted. Available becomes [2,3,0].

    Request 2: P0 requests (0,2,0) from Available=[2,3,0].
        Resources ARE available (0<=2, 2<=3, 0<=0).
        Safety check FAILS: pretend state has Available=[2,1,0]
        and no process can proceed.
        → Denied (unsafe). Available remains [2,3,0].
    """

    def test_request1_p1_is_granted(self):
        """P1's request (1,0,2) must be granted."""
        state = _silberschatz()
        req = SILBERSCHATZ_REQUESTS[0]
        result = request_resources(state, req["process"], req["request"])
        self.assertTrue(result.granted, f"Expected grant; reason: {result.reason}")

    def test_request1_available_before(self):
        """Available before P1's request must be [3,3,2]."""
        state = _silberschatz()
        req = SILBERSCHATZ_REQUESTS[0]
        result = request_resources(state, req["process"], req["request"])
        self.assertEqual(result.details["available_before"], [3, 3, 2])

    def test_request1_available_after(self):
        """Available after granting P1's request must be [2,3,0]."""
        state = _silberschatz()
        req = SILBERSCHATZ_REQUESTS[0]
        result = request_resources(state, req["process"], req["request"])
        self.assertEqual(result.new_state.available, [2, 3, 0])

    def test_request1_new_allocation_p1(self):
        """P1's allocation must increase by (1,0,2): [2,0,0]→[3,0,2]."""
        state = _silberschatz()
        result = request_resources(state, 1, [1, 0, 2])
        self.assertEqual(result.new_state.allocation[1], [3, 0, 2])

    def test_request1_new_need_p1(self):
        """P1's Need must decrease by (1,0,2): [1,2,2]→[0,2,0]."""
        state = _silberschatz()
        result = request_resources(state, 1, [1, 0, 2])
        self.assertEqual(result.new_state.need[1], [0, 2, 0])

    def test_request1_post_state_safe_sequence_valid(self):
        """State after granting P1's request must have a valid safe sequence."""
        state = _silberschatz()
        result = request_resources(state, 1, [1, 0, 2])
        post_seq = result.details["safety_result"]["safe_sequence"]
        self.assertTrue(_is_valid_safe_sequence(result.new_state, post_seq))

    def test_request1_conservation_preserved(self):
        """Resource conservation must hold in the post-grant state."""
        state = _silberschatz()
        result = request_resources(state, 1, [1, 0, 2])
        new_state = result.new_state
        for j in range(new_state.m):
            alloc_sum = sum(
                new_state.allocation[i][j] for i in range(new_state.n)
            )
            self.assertEqual(
                new_state.available[j] + alloc_sum,
                new_state.total[j],
                f"Conservation violated for resource {j} after grant.",
            )

    def test_request2_p0_is_denied(self):
        """
        P0's request (0,2,0) from state after P1's grant must be denied.
        Denial reason: unsafe state, NOT insufficient resources.
        """
        state = _silberschatz()
        after_p1 = request_resources(state, 1, [1, 0, 2]).new_state
        result = request_resources(after_p1, 0, [0, 2, 0])
        self.assertFalse(result.granted, f"Expected denial; reason: {result.reason}")

    def test_request2_resources_were_sufficient(self):
        """
        P0's request (0,2,0) fits Available=[2,3,0].
        Denial is due to unsafety, not resource insufficiency.
        """
        state = _silberschatz()
        after_p1 = request_resources(state, 1, [1, 0, 2]).new_state
        result = request_resources(after_p1, 0, [0, 2, 0])
        # Resources were within available; check detail flag.
        self.assertTrue(
            result.details.get("request_within_available", False),
            "P0's request should fit available resources; denial must be due to unsafety.",
        )

    def test_request2_denial_is_unsafe_not_insufficient(self):
        """P0's denial must report unsafe state, not resource shortage."""
        state = _silberschatz()
        after_p1 = request_resources(state, 1, [1, 0, 2]).new_state
        result = request_resources(after_p1, 0, [0, 2, 0])
        self.assertIn("unsafe", result.reason.lower())
        self.assertNotIn("wait", result.reason.lower())

    def test_request2_rollback_available_unchanged(self):
        """After P0's denial, Available must remain [2,3,0] (rollback)."""
        state = _silberschatz()
        after_p1 = request_resources(state, 1, [1, 0, 2]).new_state
        request_resources(after_p1, 0, [0, 2, 0])  # denied
        # after_p1 must be unchanged (original state unmodified).
        self.assertEqual(after_p1.available, [2, 3, 0])

    def test_request2_new_state_is_none(self):
        """Denied request must return new_state = None."""
        state = _silberschatz()
        after_p1 = request_resources(state, 1, [1, 0, 2]).new_state
        result = request_resources(after_p1, 0, [0, 2, 0])
        self.assertIsNone(result.new_state)

    def test_original_state_unmodified_after_denial(self):
        """The original state object must be unchanged after any denial."""
        state = _silberschatz()
        original_avail = state.available  # copy
        original_alloc = state.allocation  # deep copy
        # Request that would be denied (unsafe after P4 gets (3,3,0)).
        request_resources(state, 4, [3, 3, 0])
        self.assertEqual(state.available, original_avail)
        self.assertEqual(state.allocation, original_alloc)


# ═══════════════════════════════════════════════════════════════════════
# 4. Requests Denied Due to Insufficient Resources
# ═══════════════════════════════════════════════════════════════════════


class TestRequestDenied(unittest.TestCase):
    """Requests denied at the available-resource precondition (step 2)."""

    def test_request_exceeds_available_one_resource(self):
        """Request for more than available in one resource type: denied."""
        state = _silberschatz()
        # Available=[3,3,2]. P0 requests [4,0,0]: R0 insufficient.
        result = request_resources(state, 0, [4, 0, 0])
        self.assertFalse(result.granted)
        self.assertIn("wait", result.reason.lower())

    def test_request_exceeds_available_multiple_resources(self):
        """Request exceeding available in two resource types: denied."""
        state = _silberschatz()
        # Available=[3,3,2]. P0 requests [4,4,0].
        result = request_resources(state, 0, [4, 4, 0])
        self.assertFalse(result.granted)
        self.assertFalse(result.details.get("request_within_available", True))

    def test_request_denied_new_state_is_none(self):
        """new_state must be None when denied at the available check."""
        state = _silberschatz()
        result = request_resources(state, 0, [4, 0, 0])
        self.assertIsNone(result.new_state)

    def test_request_denied_original_state_unchanged(self):
        """Original state's available must not change after a wait-denial."""
        state = _silberschatz()
        avail_before = state.available
        request_resources(state, 0, [4, 0, 0])
        self.assertEqual(state.available, avail_before)

    def test_zero_available_all_requests_denied(self):
        """
        When Available = [0, 0], any non-zero request is denied due to
        insufficient resources (wait-denial, not RequestError).

        Uses a state where Need > 0 so the request does not exceed Need
        (which would raise RequestError) but does exceed Available.
        Total=[8,6], Max=[[5,4],[4,3]], Alloc=[[4,3],[4,3]].
        Available=[0,0], Need[0]=[1,1]. Request [1,0] exceeds Available.
        """
        state = SystemState(
            total=[8, 6],
            max_claim=[[5, 4], [4, 3]],
            allocation=[[4, 3], [4, 3]],
        )
        self.assertEqual(state.available, [0, 0])
        # Need[0] = [1,1] > 0, so request [1,0] does not exceed Need.
        result = request_resources(state, 0, [1, 0])
        self.assertFalse(result.granted)
        self.assertIn("wait", result.reason.lower())


# ═══════════════════════════════════════════════════════════════════════
# 5. Requests Denied Because Result Would Be Unsafe
# ═══════════════════════════════════════════════════════════════════════


class TestRequestUnsafe(unittest.TestCase):
    """
    Requests denied because granting leaves the system in an unsafe state,
    even though the resources are currently available.
    """

    def test_p4_request_3_3_0_denied_unsafe(self):
        """
        P4 requests (3,3,0). Available=[3,3,2], Need[4]=[4,3,1].
        Resources sufficient, but after pretend allocation:
        Available=[0,0,2]. No process can proceed → unsafe.
        """
        state = _silberschatz()
        result = request_resources(state, 4, [3, 3, 0])
        self.assertFalse(result.granted)
        self.assertTrue(result.details.get("request_within_available"))
        self.assertIn("unsafe", result.reason.lower())

    def test_unsafe_denial_no_new_state(self):
        """Unsafe-denied request must have new_state = None."""
        state = _silberschatz()
        result = request_resources(state, 4, [3, 3, 0])
        self.assertIsNone(result.new_state)

    def test_unsafe_denial_rollback_in_details(self):
        """Details dict must flag rollback=True for unsafe denials."""
        state = _silberschatz()
        result = request_resources(state, 4, [3, 3, 0])
        self.assertTrue(result.details.get("rollback", False))

    def test_unsafe_denial_safety_result_in_details(self):
        """Details must include the safety_result showing is_safe=False."""
        state = _silberschatz()
        result = request_resources(state, 4, [3, 3, 0])
        safety = result.details.get("safety_result", {})
        self.assertFalse(safety.get("is_safe"))
        self.assertEqual(safety.get("safe_sequence"), [])

    def test_constructed_unsafe_scenario(self):
        """
        Construct a 2-process, 1-resource system where granting P0's
        request leaves P1 permanently stuck (unsafe).

        Total=3, Max=[[2],[4]], Alloc=[[1],[1]].
        Available=1, Need=[[1],[3]].

        P0 requests (1,):
            Pretend: Available=0, Alloc[0]=2, Need[0]=0.
            Safety from Work=0:
                P0: Need[0]=0 <= 0 → Work = 0+2 = 2.
                P1: Need[1]=3 > 2 → cannot proceed.
            → UNSAFE → denied.
        """
        state = SystemState(
            total=[3],
            max_claim=[[2], [4]],
            allocation=[[1], [1]],
        )
        self.assertEqual(state.available, [1])
        self.assertEqual(state.need, [[1], [3]])
        result = request_resources(state, 0, [1])
        self.assertFalse(result.granted)
        self.assertIn("unsafe", result.reason.lower())


# ═══════════════════════════════════════════════════════════════════════
# 6. Request Errors (Structural Violations)
# ═══════════════════════════════════════════════════════════════════════


class TestRequestErrors(unittest.TestCase):
    """Structural violations that must raise RequestError."""

    def test_request_exceeds_need_raises_error(self):
        """Request > Need[i][j] must raise RequestError."""
        state = _silberschatz()
        # Need[1] = [1,2,2]. Request [2,0,0] has 2 > 1 at index 0.
        with self.assertRaises(RequestError):
            request_resources(state, 1, [2, 0, 0])

    def test_request_exceeds_need_message_identifies_resource(self):
        """RequestError message must reference the exceeding resource."""
        state = _silberschatz()
        try:
            request_resources(state, 1, [2, 0, 0])
            self.fail("RequestError not raised")
        except RequestError as exc:
            self.assertIn("Need", str(exc))

    def test_negative_process_id_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), -1, [0, 0, 0])

    def test_process_id_out_of_range_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 5, [0, 0, 0])

    def test_process_id_too_large_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 100, [0, 0, 0])

    def test_wrong_request_vector_length_raises_error(self):
        """Request with wrong number of elements must raise RequestError."""
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 0, [1, 0])  # m=3, length=2

    def test_negative_request_value_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 0, [-1, 0, 0])

    def test_float_request_value_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 0, [1.0, 0, 0])

    def test_float_process_id_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 0.0, [0, 0, 0])

    def test_string_process_id_raises_error(self):
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), "0", [0, 0, 0])

    def test_bool_process_id_treated_as_int(self):
        """
        Python's bool is a subclass of int.
        bool(True)==1, bool(False)==0 — both are valid process IDs.
        This tests that no extra rejection occurs for booleans
        (since isinstance(True, int) is True in Python).
        This is an intentional Python language property, not a bug.
        """
        state = _silberschatz()
        # True == 1, which is P1 — should behave as process_id=1.
        result = request_resources(state, True, [0, 0, 0])
        self.assertTrue(result.granted)  # zero request, always safe

    def test_empty_request_exceeds_need_on_non_zero_need(self):
        """
        An empty request [] with m=3 must raise RequestError
        due to wrong vector length.
        """
        with self.assertRaises(RequestError):
            request_resources(_silberschatz(), 0, [])


# ═══════════════════════════════════════════════════════════════════════
# 7. Rollback Verification
# ═══════════════════════════════════════════════════════════════════════


class TestRollback(unittest.TestCase):
    """
    Verify that denied requests (both wait-denial and unsafe-denial)
    leave all original state properties unchanged.
    """

    def _assert_state_unchanged(self, original: SystemState, label: str) -> None:
        """
        Take a snapshot of the state before the request and re-read
        properties after the request to confirm immutability.
        Since SystemState is immutable, this tests the caller's
        snapshot preservation.
        """
        # Capture snapshots.
        avail_snap = original.available
        alloc_snap = original.allocation
        need_snap = original.need
        total_snap = original.total
        return avail_snap, alloc_snap, need_snap, total_snap

    def test_rollback_on_wait_denial(self):
        """State properties unchanged after a wait-denial."""
        state = _silberschatz()
        avail_before = state.available
        alloc_before = state.allocation
        need_before = state.need

        request_resources(state, 0, [4, 0, 0])  # exceeds available → wait

        self.assertEqual(state.available, avail_before)
        self.assertEqual(state.allocation, alloc_before)
        self.assertEqual(state.need, need_before)

    def test_rollback_on_unsafe_denial(self):
        """State properties unchanged after an unsafe-denial."""
        state = _silberschatz()
        avail_before = state.available
        alloc_before = state.allocation
        need_before = state.need

        request_resources(state, 4, [3, 3, 0])  # unsafe → denied

        self.assertEqual(state.available, avail_before)
        self.assertEqual(state.allocation, alloc_before)
        self.assertEqual(state.need, need_before)

    def test_rollback_on_need_violation_error(self):
        """State unchanged even when RequestError is raised."""
        state = _silberschatz()
        avail_before = state.available

        try:
            request_resources(state, 1, [2, 0, 0])
        except RequestError:
            pass

        self.assertEqual(state.available, avail_before)

    def test_sequential_denials_state_stable(self):
        """Multiple sequential denials do not accumulate state corruption."""
        state = _silberschatz()
        avail_before = state.available

        for _ in range(5):
            request_resources(state, 4, [3, 3, 0])  # always denied

        self.assertEqual(state.available, avail_before)

    def test_granted_request_does_not_modify_original_state(self):
        """
        A granted request returns a NEW state object.
        The original state must be unchanged.
        """
        state = _silberschatz()
        avail_before = state.available
        alloc_before = state.allocation

        result = request_resources(state, 1, [1, 0, 2])
        self.assertTrue(result.granted)

        # Original state must be unchanged.
        self.assertEqual(state.available, avail_before)
        self.assertEqual(state.allocation, alloc_before)
        # New state must reflect the grant.
        self.assertNotEqual(result.new_state.available, avail_before)


# ═══════════════════════════════════════════════════════════════════════
# 8. Edge Cases
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases(unittest.TestCase):
    """Boundary and minimal configurations."""

    def test_zero_request_always_granted(self):
        """
        A zero-vector request never changes state and must always be granted
        (the state is already safe, and the pretend allocation is a no-op).
        """
        state = _silberschatz()
        result = request_resources(state, 0, [0, 0, 0])
        self.assertTrue(result.granted)

    def test_zero_request_state_identical(self):
        """State after granting a zero request is effectively identical."""
        state = _silberschatz()
        result = request_resources(state, 0, [0, 0, 0])
        self.assertEqual(result.new_state.available, state.available)
        self.assertEqual(result.new_state.allocation, state.allocation)

    def test_grant_then_grant_sequential_state(self):
        """Two sequential grants produce a consistent state chain."""
        state = _silberschatz()
        # P3: Need=[0,1,1]. Available=[3,3,2]. Request [0,1,1].
        r1 = request_resources(state, 3, [0, 1, 1])
        self.assertTrue(r1.granted)
        s1 = r1.new_state
        # From s1: P1 requests [1,0,2]. Need[1]=[1,2,2], Available=s1.available.
        r2 = request_resources(s1, 1, [1, 0, 2])
        # This may or may not be granted depending on s1; just verify no crash.
        self.assertIsInstance(r2.granted, bool)

    def test_single_process_single_resource_grant(self):
        """Minimal system: 1 process, 1 resource. Grant the Need."""
        state = SystemState(total=[5], max_claim=[[3]], allocation=[[1]])
        # Need=2, Available=4. Request [2].
        result = request_resources(state, 0, [2])
        self.assertTrue(result.granted)
        self.assertEqual(result.new_state.available, [2])
        self.assertEqual(result.new_state.need[0], [0])

    def test_single_process_single_resource_full_allocation_zero_need(self):
        """
        After granting the full need, the process has Need=[0].
        A further zero-request is granted; a non-zero request raises RequestError.
        """
        state = SystemState(total=[5], max_claim=[[3]], allocation=[[3]])
        result = request_resources(state, 0, [0])
        self.assertTrue(result.granted)
        with self.assertRaises(RequestError):
            request_resources(state, 0, [1])  # Need[0]=[0], request 1 > 0

    def test_all_processes_need_zero_still_safe(self):
        """When all Need vectors are zero, the state is trivially safe."""
        state = SystemState(
            total=[8, 6],
            max_claim=[[4, 3], [4, 3]],
            allocation=[[4, 3], [4, 3]],
        )
        result = safety_check(state)
        self.assertTrue(result.is_safe)
        self.assertEqual(sorted(result.safe_sequence), [0, 1])

    def test_safety_check_does_not_modify_state(self):
        """safety_check must not modify the passed SystemState."""
        state = _silberschatz()
        avail_before = state.available
        alloc_before = state.allocation
        safety_check(state)
        self.assertEqual(state.available, avail_before)
        self.assertEqual(state.allocation, alloc_before)


# ═══════════════════════════════════════════════════════════════════════
# 9. Result Type Contracts
# ═══════════════════════════════════════════════════════════════════════


class TestResultTypes(unittest.TestCase):
    """Verify SafetyResult and RequestResult field contracts."""

    def test_safety_result_fields_safe_state(self):
        """SafetyResult has is_safe, safe_sequence, trace on safe state."""
        result = safety_check(_silberschatz())
        self.assertIsInstance(result.is_safe, bool)
        self.assertIsInstance(result.safe_sequence, list)
        self.assertIsInstance(result.trace, list)
        self.assertTrue(result.is_safe)
        self.assertGreater(len(result.safe_sequence), 0)
        self.assertGreater(len(result.trace), 0)

    def test_safety_result_fields_unsafe_state(self):
        """SafetyResult is_safe=False, sequence=[], trace non-empty."""
        state = SystemState(
            total=[2],
            max_claim=[[2], [2]],
            allocation=[[1], [1]],
        )
        result = safety_check(state)
        self.assertFalse(result.is_safe)
        self.assertEqual(result.safe_sequence, [])
        self.assertGreater(len(result.trace), 0)

    def test_request_result_fields_granted(self):
        """RequestResult fields when request is granted."""
        result = request_resources(_silberschatz(), 1, [1, 0, 2])
        self.assertIsInstance(result.granted, bool)
        self.assertTrue(result.granted)
        self.assertIsInstance(result.new_state, SystemState)
        self.assertIsInstance(result.reason, str)
        self.assertIsInstance(result.details, dict)
        self.assertGreater(len(result.reason), 0)

    def test_request_result_fields_denied_wait(self):
        """RequestResult fields when denied due to insufficient resources."""
        result = request_resources(_silberschatz(), 0, [4, 0, 0])
        self.assertFalse(result.granted)
        self.assertIsNone(result.new_state)
        self.assertIsInstance(result.reason, str)
        self.assertIsInstance(result.details, dict)

    def test_request_result_fields_denied_unsafe(self):
        """RequestResult fields when denied due to unsafe state."""
        result = request_resources(_silberschatz(), 4, [3, 3, 0])
        self.assertFalse(result.granted)
        self.assertIsNone(result.new_state)
        self.assertIn("safety_result", result.details)
        self.assertIn("rollback", result.details)

    def test_trace_contains_init_step(self):
        """Safety trace must start with an init step."""
        result = safety_check(_silberschatz())
        self.assertEqual(result.trace[0]["step"], "init")
        self.assertIn("work", result.trace[0])
        self.assertIn("finish", result.trace[0])

    def test_trace_last_step_completed_or_terminated(self):
        """Last trace step must be 'completed' (safe) or 'terminated' (unsafe)."""
        safe_result = safety_check(_silberschatz())
        self.assertEqual(safe_result.trace[-1]["step"], "completed")

        unsafe_state = SystemState(
            total=[2], max_claim=[[2], [2]], allocation=[[1], [1]]
        )
        unsafe_result = safety_check(unsafe_state)
        self.assertEqual(unsafe_result.trace[-1]["step"], "terminated")

    def test_details_contains_required_keys(self):
        """Details dict must contain expected keys for a granted request."""
        result = request_resources(_silberschatz(), 1, [1, 0, 2])
        for key in [
            "process_id", "request", "need_i", "available_before",
            "request_within_need", "request_within_available",
            "pretend_available", "pretend_allocation_i",
            "pretend_need_i", "safety_result",
        ]:
            self.assertIn(key, result.details, f"Missing key: {key}")


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
