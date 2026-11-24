"""
Unit Tests for Ground-Truth Validation Scenarios (src/ground_truth.py).
Verifies that both the Wait-For Graph and Multi-Instance detectors match
exact theoretical expectations across all standard benchmark cases.
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ground_truth import (
    get_all_ground_truth_cases,
    case_no_deadlock,
    case_one_deadlock_cycle,
    case_multiple_deadlock_cycles,
    case_processes_blocked_behind_deadlock,
    case_multiple_resource_instances_safe,
    case_multiple_resource_instances_deadlocked,
    case_zero_allocation,
    case_available_resources_allow_finish,
)
from src.detectors.wait_for_graph import detect_wfg_deadlock
from src.detectors.multi_instance_detector import detect_multi_instance_deadlock


class TestGroundTruthScenarios(unittest.TestCase):
    """Test suite running ground-truth scenarios against both detectors."""

    def test_case_no_deadlock(self):
        """Verify Case 1: No Deadlock."""
        case = case_no_deadlock()
        wfg_res = detect_wfg_deadlock(case.state)
        multi_res = detect_multi_instance_deadlock(case.state)

        self.assertEqual(wfg_res.is_deadlocked, case.expected_wfg_is_deadlocked)
        self.assertEqual(wfg_res.deadlocked_processes, case.expected_wfg_deadlocked_processes)
        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)

    def test_case_one_deadlock_cycle(self):
        """Verify Case 2: One Deadlock Cycle."""
        case = case_one_deadlock_cycle()
        wfg_res = detect_wfg_deadlock(case.state)
        multi_res = detect_multi_instance_deadlock(case.state)

        self.assertEqual(wfg_res.is_deadlocked, case.expected_wfg_is_deadlocked)
        self.assertEqual(wfg_res.deadlocked_processes, case.expected_wfg_deadlocked_processes)
        self.assertEqual(wfg_res.cycles, case.expected_wfg_cycles)
        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)

    def test_case_multiple_deadlock_cycles(self):
        """Verify Case 3: Multiple Deadlock Cycles."""
        case = case_multiple_deadlock_cycles()
        wfg_res = detect_wfg_deadlock(case.state)
        multi_res = detect_multi_instance_deadlock(case.state)

        self.assertEqual(wfg_res.is_deadlocked, case.expected_wfg_is_deadlocked)
        self.assertEqual(wfg_res.deadlocked_processes, case.expected_wfg_deadlocked_processes)
        self.assertEqual(len(wfg_res.cycles), len(case.expected_wfg_cycles))
        for expected_cycle in case.expected_wfg_cycles:
            self.assertIn(expected_cycle, wfg_res.cycles)
        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)

    def test_case_processes_blocked_behind_deadlock(self):
        """Verify Case 4: Processes Blocked Behind Deadlocked Processes."""
        case = case_processes_blocked_behind_deadlock()
        wfg_res = detect_wfg_deadlock(case.state)
        multi_res = detect_multi_instance_deadlock(case.state)

        # WFG must only classify cycle members as deadlocked
        self.assertEqual(wfg_res.is_deadlocked, case.expected_wfg_is_deadlocked)
        self.assertEqual(wfg_res.deadlocked_processes, case.expected_wfg_deadlocked_processes)
        self.assertEqual(wfg_res.blocked_processes, case.expected_wfg_blocked_processes)

        # Multi-Instance detector identifies all processes that cannot finish
        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)

    def test_case_multiple_resource_instances_safe(self):
        """Verify Case 5a: Canonical Safe Multi-Instance (Silberschatz §8.6.2)."""
        case = case_multiple_resource_instances_safe()
        multi_res = detect_multi_instance_deadlock(case.state)

        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)
        self.assertEqual(len(multi_res.finish_order), 5)

    def test_case_multiple_resource_instances_deadlocked(self):
        """Verify Case 5b: Canonical Deadlocked Multi-Instance (Silberschatz §8.6.2)."""
        case = case_multiple_resource_instances_deadlocked()
        multi_res = detect_multi_instance_deadlock(case.state)

        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)

    def test_case_zero_allocation(self):
        """Verify Case 6: Zero Allocation."""
        case = case_zero_allocation()
        multi_res = detect_multi_instance_deadlock(case.state)

        self.assertEqual(multi_res.is_deadlocked, case.expected_multi_is_deadlocked)
        self.assertEqual(multi_res.deadlocked_processes, case.expected_multi_deadlocked_processes)
        self.assertIn(0, multi_res.unallocated_processes)

    def test_case_available_resources_allow_finish(self):
        """Verify Case 7: Available Headroom Breaks Potential Deadlock."""
        case = case_available_resources_allow_finish()
        multi_res = detect_multi_instance_deadlock(case.state)
        wfg_res = detect_wfg_deadlock(case.state)

        self.assertFalse(multi_res.is_deadlocked)
        self.assertFalse(wfg_res.is_deadlocked)
        self.assertEqual(wfg_res.edge_count, 0)

    def test_all_ground_truth_cases_enumerable(self):
        """Verify that get_all_ground_truth_cases returns complete dictionary of valid cases."""
        all_cases = get_all_ground_truth_cases()
        self.assertEqual(len(all_cases), 8)
        for name, case in all_cases.items():
            self.assertEqual(name, case.name)
            self.assertIsNotNone(case.state)


if __name__ == "__main__":
    unittest.main()
