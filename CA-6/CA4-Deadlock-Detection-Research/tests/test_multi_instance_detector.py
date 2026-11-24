"""
Unit Tests for Multi-Instance Deadlock Detector (src/detectors/multi_instance_detector.py).
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SystemState
from src.detectors.multi_instance_detector import detect_multi_instance_deadlock


class TestMultiInstanceDetector(unittest.TestCase):
    """Test suite for the standard Multi-Instance Deadlock Detection Algorithm."""

    def test_canonical_silberschatz_safe(self):
        """Test Silberschatz §8.6.2 canonical safe multi-instance scenario."""
        # 5 processes, 3 resource types: Total = [7, 2, 6], Available = [0, 0, 0]
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

        res = detect_multi_instance_deadlock(state)
        self.assertFalse(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [])
        # All 5 processes should finish
        self.assertEqual(len(res.finish_order), 5)
        # P0 and P2 have Request == [0, 0, 0], so P0 finishes first, then P2
        self.assertEqual(res.finish_order[0], 0)
        self.assertEqual(res.finish_order[1], 2)
        # Final work should equal total system resources
        self.assertEqual(res.final_work, [7, 2, 6])

    def test_canonical_silberschatz_deadlocked(self):
        """Test Silberschatz §8.6.2 canonical deadlocked scenario where P2 requests [0, 0, 1]."""
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
                [0, 0, 1],  # Modified request
                [1, 0, 0],
                [0, 0, 2],
            ],
            available=[0, 0, 0],
        )

        res = detect_multi_instance_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [1, 2, 3, 4])
        # Only P0 finishes
        self.assertEqual(res.finish_order, [0])
        # Final work reflects Available + Allocation[0] = [0, 0, 0] + [0, 1, 0] = [0, 1, 0]
        self.assertEqual(res.final_work, [0, 1, 0])

    def test_zero_allocation_processes_initialized_to_finish(self):
        """Test that processes with Allocation == [0, ..., 0] are marked Finish=True in Step 2."""
        state = SystemState(
            total=[3, 3],
            allocation=[
                [0, 0],  # P0 holds 0
                [2, 1],  # P1 holds resources
                [0, 0],  # P2 holds 0
            ],
            request=[
                [1, 1],
                [0, 0],
                [2, 2],
            ],
            available=[1, 2],
        )

        res = detect_multi_instance_deadlock(state)
        self.assertFalse(res.is_deadlocked)
        # P0 and P2 are marked finished at initialization
        self.assertIn(0, res.unallocated_processes)
        self.assertIn(2, res.unallocated_processes)
        # P1 finishes by acquiring needed resources
        self.assertIn(1, res.finish_order)

    def test_cascading_resource_recovery(self):
        """Test that resources recovered from earlier processes unlock later processes."""
        # P0 needs [1, 0] and has [0, 1]. Available is [1, 0].
        # P0 finishes, releasing [0, 1]. Now Available becomes [1, 1].
        # P1 needs [1, 1] and has [1, 0]. P1 can now finish!
        state = SystemState(
            total=[2, 1],
            allocation=[
                [0, 1],
                [1, 0],
            ],
            request=[
                [1, 0],
                [1, 1],
            ],
            available=[1, 0],
        )

        res = detect_multi_instance_deadlock(state)
        self.assertFalse(res.is_deadlocked)
        self.assertEqual(res.finish_order, [0, 1])
        self.assertEqual(res.final_work, [2, 1])

    def test_all_processes_deadlocked(self):
        """Test scenario where every process is deadlocked and none can finish."""
        state = SystemState(
            total=[2, 2],
            allocation=[
                [1, 1],
                [1, 1],
            ],
            request=[
                [1, 0],
                [0, 1],
            ],
            available=[0, 0],
        )

        res = detect_multi_instance_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [0, 1])
        self.assertEqual(res.finish_order, [])
        self.assertEqual(res.final_work, [0, 0])

    def test_trace_audit_trail_recorded(self):
        """Test that trace records step-by-step audit entries with correct keys."""
        state = SystemState(
            total=[1, 1],
            allocation=[[1, 0], [0, 1]],
            request=[[0, 0], [0, 0]],
            available=[0, 0],
        )
        res = detect_multi_instance_deadlock(state)
        self.assertTrue(len(res.trace) >= 3)
        self.assertEqual(res.trace[0]["step"], "initialization")
        self.assertEqual(res.trace[-1]["step"], "termination")


if __name__ == "__main__":
    unittest.main()
