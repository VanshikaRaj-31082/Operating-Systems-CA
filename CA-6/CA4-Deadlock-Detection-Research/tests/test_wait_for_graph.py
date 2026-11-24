"""
Unit Tests for Single-Instance Wait-For Graph (WFG) Detector (src/detectors/wait_for_graph.py).
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SystemState
from src.detectors.wait_for_graph import (
    build_wait_for_graph,
    find_elementary_cycles,
    find_blocked_processes,
    detect_wfg_deadlock,
)


class TestWaitForGraphDetector(unittest.TestCase):
    """Test suite for Wait-For Graph construction, DFS cycle detection, and classification."""

    def test_acyclic_graph_no_deadlock(self):
        """Test linear dependency chain without cycles."""
        # P0 holds R0, requests R1 (held by P1)
        # P1 holds R1, requests R2 (held by P2)
        # P2 holds R2, requests nothing
        state = SystemState(
            total=[1, 1, 1],
            allocation=[
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
            ],
            request=[
                [0, 1, 0],
                [0, 0, 1],
                [0, 0, 0],
            ],
            available=[0, 0, 0],
        )

        res = detect_wfg_deadlock(state)
        self.assertFalse(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [])
        self.assertEqual(res.cycles, [])
        self.assertEqual(res.blocked_processes, [])
        self.assertEqual(res.adjacency_list[0], [1])
        self.assertEqual(res.adjacency_list[1], [2])
        self.assertEqual(res.adjacency_list[2], [])

    def test_single_two_process_cycle(self):
        """Test classic 2-process circular deadlock."""
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

        res = detect_wfg_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [0, 1])
        self.assertEqual(res.cycles, [[0, 1]])
        self.assertEqual(res.blocked_processes, [])

    def test_three_process_cycle(self):
        """Test 3-process circular wait P0 -> P1 -> P2 -> P0."""
        state = SystemState(
            total=[1, 1, 1],
            allocation=[
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
            ],
            request=[
                [0, 1, 0],
                [0, 0, 1],
                [1, 0, 0],
            ],
            available=[0, 0, 0],
        )

        res = detect_wfg_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [0, 1, 2])
        self.assertEqual(res.cycles, [[0, 1, 2]])
        self.assertEqual(res.blocked_processes, [])

    def test_disjoint_multiple_cycles(self):
        """Test two independent disjoint cycles in the same graph."""
        # Cycle 1: P0 <-> P1
        # Cycle 2: P2 <-> P3
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

        res = detect_wfg_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [0, 1, 2, 3])
        self.assertEqual(len(res.cycles), 2)
        self.assertIn([0, 1], res.cycles)
        self.assertIn([2, 3], res.cycles)
        self.assertEqual(res.blocked_processes, [])

    def test_interconnected_cycles(self):
        """Test figure-8 overlapping cycles sharing a node."""
        # P0 <-> P1 and P1 <-> P2
        state = SystemState(
            total=[1, 1, 1, 1],
            allocation=[
                [1, 0, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 0, 1],
            ],
            request=[
                [0, 1, 0, 0],
                [1, 0, 0, 1],
                [0, 0, 1, 0],
            ],
            available=[0, 0, 0, 0],
        )

        res = detect_wfg_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        self.assertEqual(res.deadlocked_processes, [0, 1, 2])
        self.assertIn([0, 1], res.cycles)
        self.assertIn([1, 2], res.cycles)

    def test_blocked_process_not_classified_as_deadlocked(self):
        """
        CRITICAL TEST: Verify that a process waiting behind a deadlocked cycle
        is correctly identified in `blocked_processes` and NOT in `deadlocked_processes`.
        """
        # P0 <-> P1 on R0, R1 (Deadlock Cycle)
        # P2 holds R2, requests R0 (held by P0). P2 is blocked behind P0.
        # P3 holds R3, requests R2 (held by P2). P3 is transitively blocked behind P2.
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
                [1, 0, 0, 0],  # P2 requests R0
                [0, 0, 1, 0],  # P3 requests R2
            ],
            available=[0, 0, 0, 0],
        )

        res = detect_wfg_deadlock(state)
        self.assertTrue(res.is_deadlocked)
        # Only P0 and P1 are part of the cycle
        self.assertEqual(res.deadlocked_processes, [0, 1])
        self.assertEqual(res.cycles, [[0, 1]])
        # P2 and P3 are blocked behind the deadlock cycle
        self.assertEqual(res.blocked_processes, [2, 3])
        # Crucial assertion: blocked processes must NOT be in deadlocked_processes
        for bp in res.blocked_processes:
            self.assertNotIn(bp, res.deadlocked_processes)

    def test_available_headroom_prevents_wait_edge(self):
        """Test that if a requested resource is available, no wait edge is formed."""
        # P0 holds R0, requests R1. But R1 is FREE (Available[1] == 1, P1 does not hold R1).
        state = SystemState(
            total=[1, 1],
            allocation=[
                [1, 0],
                [0, 0],
            ],
            request=[
                [0, 1],
                [0, 0],
            ],
            available=[0, 1],
        )

        res = detect_wfg_deadlock(state)
        self.assertFalse(res.is_deadlocked)
        self.assertEqual(res.edge_count, 0)
        self.assertEqual(res.adjacency_list[0], [])

    def test_isolated_unallocated_processes(self):
        """Test system where processes have zero allocation and zero requests."""
        state = SystemState(
            total=[1, 1],
            allocation=[[0, 0], [0, 0]],
            request=[[0, 0], [0, 0]],
            available=[1, 1],
        )
        res = detect_wfg_deadlock(state)
        self.assertFalse(res.is_deadlocked)
        self.assertEqual(res.edge_count, 0)
        self.assertEqual(res.deadlocked_processes, [])


if __name__ == "__main__":
    unittest.main()
