"""
CA2 - Deadlock Detection and Avoidance
Phase 1 Tests: Matrix validation, resource conservation, Need calculation,
               pressure calculation, and invariant violation detection.

These tests verify the correctness of SystemState construction,
derived-value computation, invariant enforcement, and defensive
properties (deep-copy isolation).

Test categories:
    TestValidConstruction      - Correct derived values from valid inputs.
    TestConservationLaw        - Available + sum(Allocation) = Total.
    TestNeedCalculation        - Need = Max - Allocation.
    TestPressureMetrics        - rho_j and rho_max computation.
    TestInvariantViolations    - Rejection of all invalid configurations.
    TestBoundaryConditions     - Edge cases (minimal, maximal, saturated).
    TestDeepCopyIsolation      - Input/output mutation safety.
    TestDisplayMethods         - repr and format_matrices output.
"""

import unittest
import sys
import os

# Ensure src/ is importable from the tests/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.models import SystemState, InvariantViolation
from src.config import (
    SILBERSCHATZ_TOTAL,
    SILBERSCHATZ_MAX,
    SILBERSCHATZ_ALLOCATION,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Valid Construction and Derived Values
# ═══════════════════════════════════════════════════════════════════════

class TestValidConstruction(unittest.TestCase):
    """Verify that valid configurations produce correct derived state."""

    def test_silberschatz_dimensions(self):
        """Canonical example has 5 processes and 3 resource types."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        self.assertEqual(state.n, 5)
        self.assertEqual(state.m, 3)

    def test_silberschatz_total(self):
        """Total vector is preserved unchanged."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        self.assertEqual(state.total, [10, 5, 7])

    def test_silberschatz_available(self):
        """Available = Total - sum(Allocation) = [3, 3, 2]."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        self.assertEqual(state.available, [3, 3, 2])

    def test_minimal_system(self):
        """Smallest valid system: 1 process, 1 resource type."""
        state = SystemState(total=[5], max_claim=[[3]], allocation=[[1]])
        self.assertEqual(state.n, 1)
        self.assertEqual(state.m, 1)
        self.assertEqual(state.available, [4])
        self.assertEqual(state.need, [[2]])

    def test_zero_allocation(self):
        """No resources allocated: Available equals Total."""
        state = SystemState(
            total=[10, 5],
            max_claim=[[5, 3], [4, 2]],
            allocation=[[0, 0], [0, 0]],
        )
        self.assertEqual(state.available, [10, 5])
        self.assertEqual(state.need, [[5, 3], [4, 2]])

    def test_full_allocation(self):
        """Allocation == Max: Need is zero, processes can finish immediately."""
        state = SystemState(
            total=[10, 8],
            max_claim=[[5, 3], [5, 5]],
            allocation=[[5, 3], [5, 5]],
        )
        self.assertEqual(state.available, [0, 0])
        self.assertEqual(state.need, [[0, 0], [0, 0]])

    def test_max_equals_zero(self):
        """Process with Max=0 and Allocation=0 is valid (no claims)."""
        state = SystemState(
            total=[5],
            max_claim=[[0], [3]],
            allocation=[[0], [1]],
        )
        self.assertEqual(state.need, [[0], [2]])
        self.assertEqual(state.available, [4])

    def test_many_processes_few_resources(self):
        """10 processes sharing 2 resource types."""
        n, m = 10, 2
        total = [20, 15]
        max_claim = [[2, 1]] * n
        allocation = [[1, 0]] * n
        state = SystemState(total=total, max_claim=max_claim, allocation=allocation)
        self.assertEqual(state.n, 10)
        self.assertEqual(state.m, 2)
        self.assertEqual(state.available, [10, 15])

    def test_single_resource_saturated(self):
        """All capacity allocated to processes, Available = 0."""
        state = SystemState(
            total=[6],
            max_claim=[[3], [3]],
            allocation=[[3], [3]],
        )
        self.assertEqual(state.available, [0])


# ═══════════════════════════════════════════════════════════════════════
# 2. Conservation Law
# ═══════════════════════════════════════════════════════════════════════

class TestConservationLaw(unittest.TestCase):
    """Verify Available[j] + sum_i(Allocation[i][j]) = Total[j]."""

    def test_silberschatz_conservation(self):
        """Conservation holds for every resource type in canonical example."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        for j in range(state.m):
            alloc_sum = sum(state.allocation[i][j] for i in range(state.n))
            self.assertEqual(
                state.available[j] + alloc_sum,
                state.total[j],
                f"Conservation violated for resource type {j}",
            )

    def test_conservation_with_zero_allocation(self):
        """When nothing is allocated, Available equals Total."""
        state = SystemState(
            total=[7, 3, 5],
            max_claim=[[2, 1, 3], [4, 2, 1]],
            allocation=[[0, 0, 0], [0, 0, 0]],
        )
        for j in range(state.m):
            self.assertEqual(state.available[j], state.total[j])

    def test_conservation_with_full_allocation(self):
        """When everything is allocated, Available is zero for all types."""
        state = SystemState(
            total=[8, 6],
            max_claim=[[5, 4], [3, 2]],
            allocation=[[5, 4], [3, 2]],
        )
        for j in range(state.m):
            alloc_sum = sum(state.allocation[i][j] for i in range(state.n))
            self.assertEqual(alloc_sum, state.total[j])
            self.assertEqual(state.available[j], 0)

    def test_conservation_multiple_processes(self):
        """Conservation holds across varying allocation patterns."""
        state = SystemState(
            total=[15, 10, 8],
            max_claim=[
                [5, 4, 3],
                [4, 3, 2],
                [6, 3, 3],
            ],
            allocation=[
                [2, 1, 1],
                [3, 2, 0],
                [4, 1, 2],
            ],
        )
        # sum(Allocation): [9, 4, 3]
        # Available: [6, 6, 5]
        for j in range(state.m):
            alloc_sum = sum(state.allocation[i][j] for i in range(state.n))
            self.assertEqual(state.available[j] + alloc_sum, state.total[j])


# ═══════════════════════════════════════════════════════════════════════
# 3. Need Calculation
# ═══════════════════════════════════════════════════════════════════════

class TestNeedCalculation(unittest.TestCase):
    """Verify Need[i][j] = Max[i][j] - Allocation[i][j] for all i, j."""

    def test_silberschatz_need(self):
        """Canonical Need matrix matches hand-computed values."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        expected_need = [
            [7, 4, 3],  # P0: Max=[7,5,3] - Alloc=[0,1,0]
            [1, 2, 2],  # P1: Max=[3,2,2] - Alloc=[2,0,0]
            [6, 0, 0],  # P2: Max=[9,0,2] - Alloc=[3,0,2]
            [0, 1, 1],  # P3: Max=[2,2,2] - Alloc=[2,1,1]
            [4, 3, 1],  # P4: Max=[4,3,3] - Alloc=[0,0,2]
        ]
        self.assertEqual(state.need, expected_need)

    def test_need_element_wise(self):
        """Need[i][j] = Max[i][j] - Allocation[i][j] for every cell."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        for i in range(state.n):
            for j in range(state.m):
                self.assertEqual(
                    state.need[i][j],
                    state.max_claim[i][j] - state.allocation[i][j],
                    f"Need[{i}][{j}] incorrect",
                )

    def test_need_zero_when_fully_allocated(self):
        """Need is zero vector when Allocation equals Max."""
        state = SystemState(
            total=[10],
            max_claim=[[5], [5]],
            allocation=[[5], [5]],
        )
        for i in range(state.n):
            for j in range(state.m):
                self.assertEqual(state.need[i][j], 0)

    def test_need_equals_max_when_nothing_allocated(self):
        """Need equals Max when Allocation is all zeros."""
        max_claim = [[3, 4], [5, 2]]
        state = SystemState(
            total=[10, 10],
            max_claim=max_claim,
            allocation=[[0, 0], [0, 0]],
        )
        self.assertEqual(state.need, max_claim)

    def test_need_non_negative(self):
        """Need is always non-negative because Allocation <= Max is enforced."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        for i in range(state.n):
            for j in range(state.m):
                self.assertGreaterEqual(
                    state.need[i][j], 0,
                    f"Need[{i}][{j}] is negative",
                )


# ═══════════════════════════════════════════════════════════════════════
# 4. Pressure Metrics
# ═══════════════════════════════════════════════════════════════════════

class TestPressureMetrics(unittest.TestCase):
    """Verify per-resource pressure rho_j and rho_max calculation."""

    def test_silberschatz_pressure_values(self):
        """
        Verify rho_j for canonical example.
            rho_0 = (7+1+6+0+4)/10 = 18/10 = 1.8
            rho_1 = (4+2+0+1+3)/5  = 10/5  = 2.0
            rho_2 = (3+2+0+1+1)/7  =  7/7  = 1.0
        """
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        pressures = state.resource_pressure()
        self.assertAlmostEqual(pressures[0], 1.8, places=4)
        self.assertAlmostEqual(pressures[1], 2.0, places=4)
        self.assertAlmostEqual(pressures[2], 1.0, places=4)

    def test_silberschatz_max_pressure(self):
        """rho_max = max(1.8, 2.0, 1.0) = 2.0."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        self.assertAlmostEqual(state.max_pressure(), 2.0, places=4)

    def test_zero_pressure_when_fully_allocated(self):
        """When all processes are fully allocated, Need=0, so rho_j=0."""
        state = SystemState(
            total=[10],
            max_claim=[[5], [5]],
            allocation=[[5], [5]],
        )
        self.assertAlmostEqual(state.resource_pressure()[0], 0.0)

    def test_pressure_exceeds_one(self):
        """
        Pressure is a metric, not a probability; values > 1.0 are valid.
        rho_0 = (4 + 4) / 4 = 2.0.
        """
        state = SystemState(
            total=[4],
            max_claim=[[4], [4]],
            allocation=[[0], [0]],
        )
        self.assertAlmostEqual(state.resource_pressure()[0], 2.0)

    def test_pressure_below_one(self):
        """Low pressure: total demand is less than total capacity."""
        state = SystemState(
            total=[20],
            max_claim=[[3], [2]],
            allocation=[[1], [1]],
        )
        # Need = [[2], [1]], sum(Need) = 3
        # rho_0 = 3 / 20 = 0.15
        self.assertAlmostEqual(state.resource_pressure()[0], 0.15)

    def test_pressure_per_resource_independent(self):
        """Each rho_j is computed independently per resource type."""
        state = SystemState(
            total=[10, 2],
            max_claim=[[5, 2], [5, 0]],
            allocation=[[0, 0], [0, 0]],
        )
        pressures = state.resource_pressure()
        # rho_0 = (5+5)/10 = 1.0
        # rho_1 = (2+0)/2  = 1.0
        self.assertAlmostEqual(pressures[0], 1.0)
        self.assertAlmostEqual(pressures[1], 1.0)

    def test_pressure_report_sorted_descending(self):
        """pressure_report returns (index, rho_j) sorted by pressure desc."""
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        report = state.pressure_report()
        # Expected order: R1 (2.0), R0 (1.8), R2 (1.0)
        self.assertEqual(report[0][0], 1)  # resource index 1 is highest
        self.assertAlmostEqual(report[0][1], 2.0)
        self.assertEqual(report[1][0], 0)
        self.assertAlmostEqual(report[1][1], 1.8)
        self.assertEqual(report[2][0], 2)
        self.assertAlmostEqual(report[2][1], 1.0)


# ═══════════════════════════════════════════════════════════════════════
# 5. Invariant Violation Detection
# ═══════════════════════════════════════════════════════════════════════

class TestInvariantViolations(unittest.TestCase):
    """Verify that every invalid configuration raises InvariantViolation."""

    # ── Dimension Violations ─────────────────────────────────────────

    def test_empty_total_vector(self):
        """m = 0 is invalid."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[], max_claim=[[]], allocation=[[]])

    def test_empty_process_list(self):
        """n = 0 is invalid."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5], max_claim=[], allocation=[])

    def test_max_column_mismatch(self):
        """Max row with wrong number of columns."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5, 5], max_claim=[[3]], allocation=[[1, 1]])

    def test_allocation_column_mismatch(self):
        """Allocation row with wrong number of columns."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5, 5], max_claim=[[3, 3]], allocation=[[1]])

    def test_row_count_mismatch(self):
        """Allocation has fewer rows than Max."""
        with self.assertRaises(InvariantViolation):
            SystemState(
                total=[5, 5],
                max_claim=[[3, 3], [2, 2]],
                allocation=[[1, 1]],
            )

    # ── Non-Negativity Violations ────────────────────────────────────

    def test_negative_total(self):
        with self.assertRaises(InvariantViolation):
            SystemState(total=[-1, 5], max_claim=[[1, 1]], allocation=[[0, 0]])

    def test_zero_total(self):
        """Total[j] must be > 0, not just >= 0."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[0, 5], max_claim=[[0, 1]], allocation=[[0, 0]])

    def test_negative_max(self):
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5], max_claim=[[-1]], allocation=[[0]])

    def test_negative_allocation(self):
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5], max_claim=[[3]], allocation=[[-1]])

    # ── Type Violations ──────────────────────────────────────────────

    def test_float_total(self):
        """Non-integer values are rejected."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5.5], max_claim=[[3]], allocation=[[1]])

    def test_float_max(self):
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5], max_claim=[[3.0]], allocation=[[1]])

    def test_float_allocation(self):
        with self.assertRaises(InvariantViolation):
            SystemState(total=[5], max_claim=[[3]], allocation=[[1.0]])

    # ── Allocation Bound Violations ──────────────────────────────────

    def test_allocation_exceeds_max(self):
        """Allocation[i][j] > Max[i][j] is invalid."""
        with self.assertRaises(InvariantViolation):
            SystemState(total=[10], max_claim=[[3]], allocation=[[4]])

    def test_allocation_exceeds_max_single_cell(self):
        """Even one cell exceeding Max is rejected."""
        with self.assertRaises(InvariantViolation):
            SystemState(
                total=[10, 10],
                max_claim=[[5, 3]],
                allocation=[[5, 4]],  # col 1: 4 > 3
            )

    # ── Conservation / Over-Allocation Violations ────────────────────

    def test_over_allocation(self):
        """sum(Allocation) > Total produces negative Available."""
        with self.assertRaises(InvariantViolation):
            SystemState(
                total=[5],
                max_claim=[[4], [4]],
                allocation=[[3], [3]],  # sum = 6 > 5
            )

    def test_over_allocation_one_resource_type(self):
        """Over-allocation in one resource type even if others are fine."""
        with self.assertRaises(InvariantViolation):
            SystemState(
                total=[10, 3],
                max_claim=[[5, 2], [5, 2]],
                allocation=[[3, 2], [3, 2]],  # col 1: sum=4 > 3
            )


# ═══════════════════════════════════════════════════════════════════════
# 6. Boundary Conditions
# ═══════════════════════════════════════════════════════════════════════

class TestBoundaryConditions(unittest.TestCase):
    """Test edge cases at system boundaries."""

    def test_available_exactly_zero(self):
        """Available = 0 is valid (not negative)."""
        state = SystemState(
            total=[6],
            max_claim=[[3], [3]],
            allocation=[[3], [3]],
        )
        self.assertEqual(state.available, [0])

    def test_single_resource_single_process(self):
        """Minimal system dimensions."""
        state = SystemState(total=[1], max_claim=[[1]], allocation=[[0]])
        self.assertEqual(state.available, [1])
        self.assertEqual(state.need, [[1]])

    def test_allocation_equals_max_for_some_processes(self):
        """Mix of fully allocated and partially allocated processes."""
        state = SystemState(
            total=[10, 10],
            max_claim=[[5, 5], [5, 5]],
            allocation=[[5, 5], [2, 3]],  # P0 fully allocated, P1 partial
        )
        self.assertEqual(state.need[0], [0, 0])
        self.assertEqual(state.need[1], [3, 2])
        self.assertEqual(state.available, [3, 2])

    def test_max_equals_total_for_single_process(self):
        """One process claims the entire resource pool."""
        state = SystemState(
            total=[10],
            max_claim=[[10]],
            allocation=[[5]],
        )
        self.assertEqual(state.need, [[5]])
        self.assertEqual(state.available, [5])


# ═══════════════════════════════════════════════════════════════════════
# 7. Deep-Copy Isolation
# ═══════════════════════════════════════════════════════════════════════

class TestDeepCopyIsolation(unittest.TestCase):
    """Verify that external mutation cannot corrupt internal state."""

    def test_input_mutation_does_not_affect_state(self):
        """Mutating input lists after construction has no effect."""
        total = [10, 5, 7]
        max_claim = [[7, 5, 3], [3, 2, 2]]
        allocation = [[0, 1, 0], [2, 0, 0]]

        state = SystemState(
            total=total, max_claim=max_claim, allocation=allocation
        )

        # Mutate all inputs.
        total[0] = 999
        max_claim[0][0] = 999
        allocation[0][0] = 999

        # State must be unchanged.
        self.assertEqual(state.total, [10, 5, 7])
        self.assertEqual(state.max_claim[0], [7, 5, 3])
        self.assertEqual(state.allocation[0], [0, 1, 0])

    def test_output_mutation_does_not_affect_state(self):
        """Mutating returned property values has no effect."""
        state = SystemState(
            total=[10, 5],
            max_claim=[[5, 3]],
            allocation=[[1, 1]],
        )

        # Mutate returned values.
        state.available[0] = 999
        state.total[0] = 999
        state.need[0][0] = 999
        state.max_claim[0][0] = 999
        state.allocation[0][0] = 999

        # Internal state must be unchanged.
        self.assertEqual(state.available, [9, 4])
        self.assertEqual(state.total, [10, 5])
        self.assertEqual(state.need, [[4, 2]])
        self.assertEqual(state.max_claim, [[5, 3]])
        self.assertEqual(state.allocation, [[1, 1]])


# ═══════════════════════════════════════════════════════════════════════
# 8. Display Methods
# ═══════════════════════════════════════════════════════════════════════

class TestDisplayMethods(unittest.TestCase):
    """Verify repr and format_matrices produce expected output."""

    def test_repr_contains_dimensions(self):
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        r = repr(state)
        self.assertIn("n=5", r)
        self.assertIn("m=3", r)
        self.assertIn("Total=[10, 5, 7]", r)
        self.assertIn("Available=[3, 3, 2]", r)

    def test_format_matrices_contains_all_sections(self):
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        output = state.format_matrices()
        for section in ["Allocation:", "Max:", "Need", "Pressure"]:
            self.assertIn(section, output, f"Missing section: {section}")

    def test_format_matrices_contains_pressure_values(self):
        state = SystemState(
            total=SILBERSCHATZ_TOTAL,
            max_claim=SILBERSCHATZ_MAX,
            allocation=SILBERSCHATZ_ALLOCATION,
        )
        output = state.format_matrices()
        self.assertIn("1.8", output)
        self.assertIn("2.0", output)
        self.assertIn("1.0", output)


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)

