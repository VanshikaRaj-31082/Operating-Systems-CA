"""
Comprehensive Unit Tests for Workload Generators (src/generators/).
Validates reproducibility, matrix invariants, pattern fidelity, and detector compatibility.
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SystemState
from src.detectors.wait_for_graph import (
    detect_wfg_deadlock,
    build_wait_for_graph,
    find_elementary_cycles,
)
from src.detectors.multi_instance_detector import detect_multi_instance_deadlock
from src.generators import (
    GeneratorError,
    generate_acyclic_workload,
    generate_circular_workload,
    generate_random_workload,
    generate_mixed_workload,
    MixedWorkloadSpec,
)


class TestWorkloadGenerators(unittest.TestCase):
    """Test suite covering all four workload generators and regression tests."""

    # ─────────────────────────────────────────────────────────────────
    # 1. Acyclic Pattern Tests
    # ─────────────────────────────────────────────────────────────────

    def test_acyclic_pattern_dimensions_and_invariants(self):
        """Test that generate_acyclic_workload produces valid SystemState with conservation."""
        state = generate_acyclic_workload(n=5, m=4, total_per_type=1, seed=42)
        self.assertEqual(state.n, 5)
        self.assertEqual(state.m, 4)
        self.assertTrue(state.is_single_instance)

        # Conservation check: Available + sum(Allocation) == Total
        for j in range(state.m):
            alloc_sum = sum(state.allocation[i][j] for i in range(state.n))
            self.assertEqual(state.available[j] + alloc_sum, state.total[j])

    def test_acyclic_pattern_is_deadlock_free(self):
        """Verify that acyclic workloads are verified as deadlock-free by both detectors."""
        state = generate_acyclic_workload(n=6, m=6, total_per_type=1, include_blocked=True, seed=123)

        wfg_res = detect_wfg_deadlock(state)
        multi_res = detect_multi_instance_deadlock(state)

        self.assertFalse(wfg_res.is_deadlocked, "Acyclic pattern must not contain WFG cycles")
        self.assertEqual(wfg_res.deadlocked_processes, [])
        self.assertFalse(multi_res.is_deadlocked, "Acyclic pattern must terminate cleanly in multi-instance")
        self.assertEqual(multi_res.deadlocked_processes, [])

    def test_acyclic_pattern_boundary_cases(self):
        """Test single-process and single-resource boundary cases."""
        # n = 1, m = 1
        state_1 = generate_acyclic_workload(n=1, m=1, total_per_type=1)
        self.assertEqual(state_1.n, 1)
        self.assertEqual(state_1.m, 1)

        # Multi-instance acyclic
        state_multi = generate_acyclic_workload(n=4, m=3, total_per_type=5, seed=99)
        self.assertEqual(state_multi.total, [5, 5, 5])
        self.assertFalse(state_multi.is_single_instance)

    def test_acyclic_pattern_invalid_parameters(self):
        """Test that invalid inputs raise GeneratorError."""
        with self.assertRaises(GeneratorError):
            generate_acyclic_workload(n=0, m=3)
        with self.assertRaises(GeneratorError):
            generate_acyclic_workload(n=3, m=0)
        with self.assertRaises(GeneratorError):
            generate_acyclic_workload(n=3, m=3, total_per_type=0)

    # ─────────────────────────────────────────────────────────────────
    # 2. Circular Pattern Tests
    # ─────────────────────────────────────────────────────────────────

    def test_circular_pattern_single_instance_deadlock(self):
        """Verify that circular workloads contain verified deadlock cycles."""
        state = generate_circular_workload(n=4, m=4, cycle_size=3, total_per_type=1, seed=42)

        wfg_res = detect_wfg_deadlock(state)
        multi_res = detect_multi_instance_deadlock(state)

        self.assertTrue(wfg_res.is_deadlocked)
        # First 3 processes form the cycle [0, 1, 2]
        self.assertEqual(wfg_res.deadlocked_processes, [0, 1, 2])
        self.assertEqual(len(wfg_res.cycles), 1)
        self.assertEqual(wfg_res.cycles[0], [0, 1, 2])

        self.assertTrue(multi_res.is_deadlocked)
        self.assertIn(0, multi_res.deadlocked_processes)
        self.assertIn(1, multi_res.deadlocked_processes)
        self.assertIn(2, multi_res.deadlocked_processes)

    def test_circular_pattern_multi_instance_deadlock(self):
        """Verify that multi-instance circular patterns genuinely deadlock."""
        state = generate_circular_workload(n=3, m=3, cycle_size=3, total_per_type=4, seed=42)

        multi_res = detect_multi_instance_deadlock(state)
        self.assertTrue(multi_res.is_deadlocked, "Multi-instance circular workload must be deadlocked")
        self.assertEqual(multi_res.deadlocked_processes, [0, 1, 2])

    def test_circular_pattern_blocked_tail(self):
        """Verify that processes outside the cycle are properly classified as blocked behind deadlock."""
        state = generate_circular_workload(
            n=5, m=5, cycle_size=3, total_per_type=1, include_blocked_tail=True, seed=42
        )

        wfg_res = detect_wfg_deadlock(state)
        # Cycle members: 0, 1, 2
        self.assertEqual(wfg_res.deadlocked_processes, [0, 1, 2])
        # Processes 3 and 4 should be blocked behind the cycle
        self.assertEqual(wfg_res.blocked_processes, [3, 4])

    def test_circular_pattern_invalid_parameters(self):
        """Test invalid circular pattern arguments."""
        with self.assertRaises(GeneratorError):
            generate_circular_workload(n=1, m=3)  # n < 2
        with self.assertRaises(GeneratorError):
            generate_circular_workload(n=3, m=1)  # m < 2
        with self.assertRaises(GeneratorError):
            generate_circular_workload(n=3, m=3, cycle_size=5)  # cycle_size > min(n, m)
        with self.assertRaises(GeneratorError):
            generate_circular_workload(n=3, m=3, cycle_size=1)  # cycle_size < 2

    # ─────────────────────────────────────────────────────────────────
    # 3. Random Pattern Tests
    # ─────────────────────────────────────────────────────────────────

    def test_random_pattern_reproducibility(self):
        """Test that identical seeds generate identical SystemState instances."""
        state1 = generate_random_workload(n=10, m=5, total_per_type=3, seed=777)
        state2 = generate_random_workload(n=10, m=5, total_per_type=3, seed=777)
        state_diff = generate_random_workload(n=10, m=5, total_per_type=3, seed=888)

        self.assertEqual(state1, state2, "Identical seeds must produce equal states")
        self.assertNotEqual(state1, state_diff, "Different seeds should produce different states")

    def test_random_pattern_conservation_guarantee(self):
        """Test conservation law across multiple random workloads with varied densities."""
        for seed in range(20):
            state = generate_random_workload(
                n=8,
                m=6,
                total_per_type=5,
                allocation_ratio=0.8,
                request_probability=0.6,
                seed=seed,
            )
            for j in range(state.m):
                alloc_sum = sum(state.allocation[i][j] for i in range(state.n))
                self.assertEqual(
                    state.available[j] + alloc_sum,
                    state.total[j],
                    f"Conservation violated for resource {j} at seed {seed}",
                )

    def test_random_pattern_detector_compatibility(self):
        """Test that generated random states can be evaluated by both detection algorithms."""
        state = generate_random_workload(n=7, m=4, total_per_type=2, seed=42)
        # Must execute without throwing exceptions
        wfg_res = detect_wfg_deadlock(state)
        multi_res = detect_multi_instance_deadlock(state)
        self.assertIsInstance(wfg_res.is_deadlocked, bool)
        self.assertIsInstance(multi_res.is_deadlocked, bool)

    def test_random_pattern_single_instance_allocations(self):
        """Verify that single-instance random workloads can contain non-zero allocations and valid edges."""
        non_zero_alloc_found = False
        for s in range(10):
            st = generate_random_workload(n=5, m=5, total_per_type=1, allocation_ratio=0.7, seed=s)
            tot_alloc = sum(sum(row) for row in st.allocation)
            if tot_alloc > 0:
                non_zero_alloc_found = True
            # Invariant checks
            for j in range(st.m):
                col_sum = sum(st.allocation[i][j] for i in range(st.n))
                self.assertLessEqual(col_sum, st.total[j])
                self.assertEqual(st.available[j] + col_sum, st.total[j])
        self.assertTrue(non_zero_alloc_found, "Single-instance random workloads must be capable of allocating resources")

    def test_random_pattern_boundary_ratios(self):
        """Test allocation_ratio=0.0 (zero allocations) and allocation_ratio=1.0 (full allocation)."""
        st_zero = generate_random_workload(n=5, m=4, total_per_type=3, allocation_ratio=0.0, seed=42)
        total_alloc_zero = sum(sum(row) for row in st_zero.allocation)
        self.assertEqual(total_alloc_zero, 0)
        self.assertEqual(st_zero.available, st_zero.total)

        st_full = generate_random_workload(n=5, m=4, total_per_type=3, allocation_ratio=1.0, seed=42)
        total_alloc_full = sum(sum(row) for row in st_full.allocation)
        self.assertEqual(total_alloc_full, sum(st_full.total))
        self.assertEqual(st_full.available, [0] * st_full.m)

    def test_random_pattern_multi_instance_expected_behaviour(self):
        """Test statistical expectation of Binomial allocation over a large seeded sample."""
        total_units = 0
        allocated_units = 0
        target_ratio = 0.7
        cap = 5
        m = 10
        # Over 50 runs, sample size = 50 * 10 * 5 = 2500 Bernoulli trials
        for s in range(50):
            st = generate_random_workload(n=10, m=m, total_per_type=cap, allocation_ratio=target_ratio, seed=s)
            allocated_units += sum(sum(row) for row in st.allocation)
            total_units += sum(st.total)

        empirical_ratio = allocated_units / total_units
        self.assertAlmostEqual(empirical_ratio, target_ratio, delta=0.05,
                               msg=f"Empirical ratio {empirical_ratio:.3f} deviates excessively from target {target_ratio}")

    def test_random_pattern_invalid_parameters(self):
        """Test invalid random generator bounds."""
        with self.assertRaises(GeneratorError):
            generate_random_workload(n=0, m=2)
        with self.assertRaises(GeneratorError):
            generate_random_workload(n=2, m=2, allocation_ratio=1.5)
        with self.assertRaises(GeneratorError):
            generate_random_workload(n=2, m=2, request_probability=-0.1)

    # ─────────────────────────────────────────────────────────────────
    # 4. Mixed Pattern Tests
    # ─────────────────────────────────────────────────────────────────

    def test_mixed_pattern_cohort_classification(self):
        """Verify that mixed workload properly partitions deadlocked, blocked, and safe cohorts."""
        spec = generate_mixed_workload(
            n=6, m=6, deadlock_count=3, blocked_count=2, total_per_type=1, seed=42
        )

        self.assertEqual(spec.deadlocked_cohort, [0, 1, 2])
        self.assertEqual(spec.blocked_cohort, [3, 4])
        self.assertEqual(spec.safe_cohort, [5])

        wfg_res = detect_wfg_deadlock(spec.state)
        multi_res = detect_multi_instance_deadlock(spec.state)

        # WFG checks: deadlocked matches cycle, blocked matches tail, safe is neither
        self.assertTrue(wfg_res.is_deadlocked)
        self.assertEqual(wfg_res.deadlocked_processes, spec.deadlocked_cohort)
        self.assertEqual(wfg_res.blocked_processes, spec.blocked_cohort)
        self.assertNotIn(5, wfg_res.deadlocked_processes)
        self.assertNotIn(5, wfg_res.blocked_processes)

        # Multi-Instance checks: safe process terminates cleanly
        self.assertTrue(multi_res.is_deadlocked)
        self.assertIn(5, multi_res.finish_order)
        self.assertEqual(set(multi_res.deadlocked_processes), set(spec.deadlocked_cohort + spec.blocked_cohort))

    def test_mixed_pattern_invalid_cohort_bounds(self):
        """Test that invalid cohort partition raises GeneratorError."""
        # n = 4, but deadlock_count=3 and blocked_count=2 requires n >= 6
        with self.assertRaises(GeneratorError):
            generate_mixed_workload(n=4, m=5, deadlock_count=3, blocked_count=2)

    # ─────────────────────────────────────────────────────────────────
    # 5. Regression Test: WFG Self-Loop Handling
    # ─────────────────────────────────────────────────────────────────

    def test_wfg_self_loop_prevention_and_handling(self):
        """
        Regression Test: Verify that a process holding and requesting the same resource
        does not form a self-loop (Pi -> Pi) in the Wait-For Graph.
        Also verify that if an adjacency list explicitly contains a self-edge {0: [0]},
        the cycle detector handles it cleanly as a 1-node cycle [0] without infinite recursion.
        """
        # Case A: SystemState where P0 holds R0 and requests R0
        # In real OS semantics, a process does not wait on itself for a resource it already owns.
        state = SystemState(
            total=[2],
            allocation=[[1]],
            request=[[1]],
            available=[1],
        )
        adj = build_wait_for_graph(state)
        self.assertEqual(adj[0], [], "build_wait_for_graph must never create self-edges (j != i)")

        # Case B: Direct cycle detector handling of a synthetic self-loop
        synthetic_adj = {0: [0]}
        cycles = find_elementary_cycles(synthetic_adj, n=1)
        self.assertEqual(cycles, [[0]], "Self-loops must be detected as elementary cycle [0]")


if __name__ == "__main__":
    unittest.main()
