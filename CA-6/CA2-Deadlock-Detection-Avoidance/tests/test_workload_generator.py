"""
CA2 - Deadlock Detection and Avoidance
Phase 4 Tests: Workload Generator & Systematic Boundary Sweep.

Test Categories:
    TestReproducibility        - Identical seeds yield identical states; different seeds vary.
    TestInvariantEnforcement   - Conservation, allocation <= max, need = max - alloc.
    TestConfigurability        - Configurable n, m, total capacity, and pressure.
    TestRequestGeneration      - Zero, random, and deadlock request matrix validation.
    TestCharacteristicWorkloads - Safe, unsafe, and deadlocked workload generators.
    TestBoundarySweep          - Capacity variation, pressure calculation, invariant preservation.
    TestDimensionSweep         - Sweeping across multiple (n, m) dimensions.
    TestScalingGrid            - Grid generation for scaling benchmarks.
    TestAlgorithmCompatibility - Full interoperability with banker's and detector modules.
    TestInputValidation        - Rejection of invalid dimensions, negative totals, etc.
"""

import unittest
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
)

from src.models import SystemState, InvariantViolation
from src.bankers_algorithm import safety_check, request_resources
from src.deadlock_detector import detect_deadlock
from src.workload_generator import (
    GeneratorError,
    WorkloadSpec,
    BoundarySweepPoint,
    make_state,
    make_state_with_pressure,
    make_zero_request,
    make_random_request,
    make_deadlock_request,
    make_safe_state,
    make_unsafe_state,
    make_deadlocked_workload,
    boundary_sweep,
    sweep_across_dimensions,
    scaling_grid,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Reproducibility
# ═══════════════════════════════════════════════════════════════════════

class TestReproducibility(unittest.TestCase):
    """Verify that random seeds guarantee deterministic output."""

    def test_make_state_identical_with_same_seed(self):
        s1 = make_state(5, 3, [10, 10, 10], seed=123)
        s2 = make_state(5, 3, [10, 10, 10], seed=123)
        self.assertEqual(s1.allocation, s2.allocation)
        self.assertEqual(s1.max_claim, s2.max_claim)
        self.assertEqual(s1.total, s2.total)
        self.assertEqual(s1.available, s2.available)

    def test_make_state_different_with_different_seed(self):
        s1 = make_state(5, 3, [20, 20, 20], seed=1)
        s2 = make_state(5, 3, [20, 20, 20], seed=2)
        self.assertNotEqual(s1.allocation, s2.allocation)

    def test_make_state_with_pressure_reproducible(self):
        s1 = make_state_with_pressure(4, 2, 15, pressure=0.8, seed=99)
        s2 = make_state_with_pressure(4, 2, 15, pressure=0.8, seed=99)
        self.assertEqual(s1.allocation, s2.allocation)
        self.assertEqual(s1.max_claim, s2.max_claim)

    def test_random_request_reproducible(self):
        state = make_state(4, 3, [10, 10, 10], seed=42)
        r1 = make_random_request(state, seed=777)
        r2 = make_random_request(state, seed=777)
        self.assertEqual(r1, r2)


# ═══════════════════════════════════════════════════════════════════════
# 2. Invariant Enforcement
# ═══════════════════════════════════════════════════════════════════════

class TestInvariantEnforcement(unittest.TestCase):
    """Verify generated states strictly adhere to OS invariants."""

    def test_conservation_law_holds(self):
        for n, m in [(3, 2), (5, 4), (10, 3)]:
            state = make_state(n, m, [15] * m, seed=42)
            for j in range(m):
                alloc_sum = sum(state.allocation[i][j] for i in range(n))
                self.assertEqual(state.available[j] + alloc_sum, state.total[j])
                self.assertGreaterEqual(state.available[j], 0)

    def test_allocation_bounded_by_max(self):
        state = make_state(6, 3, [20, 20, 20], seed=55)
        for i in range(state.n):
            for j in range(state.m):
                self.assertLessEqual(state.allocation[i][j], state.max_claim[i][j])

    def test_need_correctly_derived(self):
        state = make_state(5, 3, [12, 15, 18], seed=101)
        for i in range(state.n):
            for j in range(state.m):
                self.assertEqual(
                    state.need[i][j],
                    state.max_claim[i][j] - state.allocation[i][j],
                )


# ═══════════════════════════════════════════════════════════════════════
# 3. Configurability
# ═══════════════════════════════════════════════════════════════════════

class TestConfigurability(unittest.TestCase):
    """Verify arbitrary positive process, resource, and capacity dimensions."""

    def test_single_process_single_resource(self):
        state = make_state(1, 1, [5], seed=1)
        self.assertEqual(state.n, 1)
        self.assertEqual(state.m, 1)
        self.assertEqual(state.total, [5])

    def test_large_dimensions(self):
        state = make_state(25, 8, [50] * 8, seed=12)
        self.assertEqual(state.n, 25)
        self.assertEqual(state.m, 8)

    def test_heterogeneous_totals(self):
        totals = [5, 10, 15, 20]
        state = make_state(4, 4, totals, seed=33)
        self.assertEqual(state.total, totals)

    def test_pressure_scaling(self):
        s_low = make_state_with_pressure(5, 3, 20, pressure=0.3, seed=42)
        s_high = make_state_with_pressure(5, 3, 20, pressure=2.5, seed=42)
        self.assertLess(s_low.max_pressure(), s_high.max_pressure())


# ═══════════════════════════════════════════════════════════════════════
# 4. Request Matrix Generation
# ═══════════════════════════════════════════════════════════════════════

class TestRequestGeneration(unittest.TestCase):
    """Verify request matrix construction rules."""

    def test_zero_request_dimensions_and_values(self):
        req = make_zero_request(4, 3)
        self.assertEqual(len(req), 4)
        for row in req:
            self.assertEqual(row, [0, 0, 0])

    def test_random_request_bounded_by_allocation(self):
        state = make_state(5, 3, [15, 15, 15], seed=10)
        req = make_random_request(state, seed=20)
        self.assertEqual(len(req), 5)
        for i in range(5):
            self.assertEqual(len(req[i]), 3)
            for j in range(3):
                self.assertGreaterEqual(req[i][j], 0)
                self.assertLessEqual(req[i][j], state.allocation[i][j])

    def test_deadlock_request_dimensions(self):
        state = make_state(5, 3, [10, 10, 10], seed=30)
        req = make_deadlock_request(state, seed=40)
        self.assertEqual(len(req), 5)
        for row in req:
            self.assertEqual(len(row), 3)


# ═══════════════════════════════════════════════════════════════════════
# 5. Characteristic Workload Generators
# ═══════════════════════════════════════════════════════════════════════

class TestCharacteristicWorkloads(unittest.TestCase):
    """Verify generation of guaranteed safe, unsafe, and deadlocked workloads."""

    def test_make_safe_state_is_safe(self):
        state = make_safe_state(5, 3, total_per_type=25, seed=10)
        result = safety_check(state)
        self.assertTrue(result.is_safe)
        self.assertEqual(len(result.safe_sequence), 5)

    def test_make_unsafe_state_is_unsafe(self):
        state = make_unsafe_state(5, 3, total_per_type=10, seed=10)
        result = safety_check(state)
        self.assertFalse(result.is_safe)
        self.assertEqual(result.safe_sequence, [])

    def test_make_deadlocked_workload_is_deadlocked(self):
        state, req = make_deadlocked_workload(5, 3, total_per_type=10, seed=10)
        result = detect_deadlock(state, req)
        self.assertTrue(result.is_deadlocked)
        self.assertGreater(len(result.deadlocked_processes), 0)


# ═══════════════════════════════════════════════════════════════════════
# 6. Boundary Sweeps
# ═══════════════════════════════════════════════════════════════════════

class TestBoundarySweep(unittest.TestCase):
    """Verify systematic variation of capacity and pressure tracking."""

    def test_boundary_sweep_monotonic_available(self):
        base_state = make_state(4, 2, [10, 10], seed=42)
        points = boundary_sweep(
            4, 2, base_state.max_claim, base_state.allocation, seed=42
        )
        self.assertGreater(len(points), 1)

        # Step 0 should have the minimum available capacity
        for i in range(len(points) - 1):
            p_curr = points[i]
            p_next = points[i + 1]
            for j in range(2):
                self.assertLessEqual(p_curr.available[j], p_next.available[j])
                self.assertLessEqual(p_curr.total[j], p_next.total[j])

    def test_boundary_sweep_points_contain_valid_system_states(self):
        base_state = make_state(3, 2, [8, 8], seed=12)
        points = boundary_sweep(
            3, 2, base_state.max_claim, base_state.allocation, seed=12
        )
        for pt in points:
            self.assertIsInstance(pt, BoundarySweepPoint)
            self.assertIsInstance(pt.state, SystemState)
            self.assertEqual(pt.state.available, pt.available)
            self.assertAlmostEqual(pt.rho_max, max(pt.rho))

    def test_sweep_across_dimensions_output_structure(self):
        grid = sweep_across_dimensions([3, 5], [2, 3], seed=50)
        self.assertEqual(len(grid), 4)
        self.assertIn((3, 2), grid)
        self.assertIn((3, 3), grid)
        self.assertIn((5, 2), grid)
        self.assertIn((5, 3), grid)
        for (n, m), pts in grid.items():
            self.assertGreater(len(pts), 0)
            self.assertEqual(pts[0].state.n, n)
            self.assertEqual(pts[0].state.m, m)


# ═══════════════════════════════════════════════════════════════════════
# 7. Scaling Grid
# ═══════════════════════════════════════════════════════════════════════

class TestScalingGrid(unittest.TestCase):
    """Verify benchmark scaling grid generation."""

    def test_scaling_grid_counts(self):
        procs = [5, 10, 20]
        res = [3, 5]
        grid = scaling_grid(procs, res, seed=42)
        self.assertEqual(len(grid), len(procs) * len(res))

    def test_scaling_grid_spec_fields(self):
        grid = scaling_grid([5], [3], seed=42)
        spec = grid[0]
        self.assertIsInstance(spec, WorkloadSpec)
        self.assertEqual(spec.n, 5)
        self.assertEqual(spec.m, 3)
        self.assertIsInstance(spec.state, SystemState)
        self.assertGreater(spec.seed, 0)


# ═══════════════════════════════════════════════════════════════════════
# 8. Algorithm Interoperability
# ═══════════════════════════════════════════════════════════════════════

class TestAlgorithmCompatibility(unittest.TestCase):
    """Ensure generated workloads seamlessly run through Banker's and Detector."""

    def test_banker_request_with_workload(self):
        state = make_state(4, 3, [20, 20, 20], seed=88)
        # Process 0 makes a request within its Need and Available
        need0 = state.need[0]
        avail = state.available
        req = [min(need0[j], avail[j]) for j in range(state.m)]
        res = request_resources(state, 0, req)
        self.assertIn(res.granted, [True, False])

    def test_detector_with_workload(self):
        state = make_state(5, 3, [15, 15, 15], seed=99)
        req = make_random_request(state, seed=99)
        det = detect_deadlock(state, req)
        self.assertIsInstance(det.is_deadlocked, bool)
        self.assertIsInstance(det.deadlocked_processes, list)


# ═══════════════════════════════════════════════════════════════════════
# 9. Input Validation and Exceptions
# ═══════════════════════════════════════════════════════════════════════

class TestInputValidation(unittest.TestCase):
    """Verify that invalid arguments raise GeneratorError."""

    def test_invalid_dimensions(self):
        with self.assertRaises(GeneratorError):
            make_state(0, 3, [10, 10, 10])
        with self.assertRaises(GeneratorError):
            make_state(5, 0, [])
        with self.assertRaises(GeneratorError):
            make_state(-1, 2, [10, 10])

    def test_total_mismatch(self):
        with self.assertRaises(GeneratorError):
            make_state(3, 3, [10, 10])  # Length 2 instead of 3

    def test_invalid_total_values(self):
        with self.assertRaises(GeneratorError):
            make_state(3, 2, [10, 0])  # 0 is invalid
        with self.assertRaises(GeneratorError):
            make_state(3, 2, [10, -5])

    def test_invalid_pressure(self):
        with self.assertRaises(GeneratorError):
            make_state_with_pressure(3, 2, 10, pressure=0)
        with self.assertRaises(GeneratorError):
            make_state_with_pressure(3, 2, 10, pressure=-1.5)

    def test_empty_scaling_grid_inputs(self):
        with self.assertRaises(GeneratorError):
            scaling_grid([], [3])
        with self.assertRaises(GeneratorError):
            scaling_grid([5], [])


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
