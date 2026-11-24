"""Unit tests for the DFS Deadlock Detection Engine."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.deadlock_detector import DeadlockDetector
from src.models import ResourceAllocationGraph


class TestDeadlockDetector(unittest.TestCase):
    """Test suite for DeadlockDetector on various graph topologies."""

    def test_empty_graph(self) -> None:
        rag = ResourceAllocationGraph()
        result = DeadlockDetector.detect_cycle(rag)
        self.assertFalse(result.has_deadlock)
        self.assertEqual(len(result.cycle_path), 0)

    def test_acyclic_linear_dependency(self) -> None:
        """P1 holds R1, P2 holds R2. P1 requests R2. No cycle exists."""
        rag = ResourceAllocationGraph(["P1", "P2"], ["R1", "R2"])
        rag.grant_resource("P1", "R1")  # R1 -> P1
        rag.grant_resource("P2", "R2")  # R2 -> P2
        rag.add_request("P1", "R2")     # P1 -> R2
        # Graph: R1 -> P1 -> R2 -> P2 (Directed Acyclic Graph)

        result = DeadlockDetector.detect_cycle(rag)
        self.assertFalse(result.has_deadlock)
        self.assertIn("No cycle detected", result.format_cycle_path())

    def test_two_process_deadlock(self) -> None:
        """P1 holds R1, requests R2; P2 holds R2, requests R1."""
        rag = ResourceAllocationGraph(["P1", "P2"], ["R1", "R2"])
        rag.grant_resource("P1", "R1")  # R1 -> P1
        rag.grant_resource("P2", "R2")  # R2 -> P2
        rag.add_request("P1", "R2")     # P1 -> R2
        rag.add_request("P2", "R1")     # P2 -> R1
        # Cycle: P1 -> R2 -> P2 -> R1 -> P1

        result = DeadlockDetector.detect_cycle(rag)
        self.assertTrue(result.has_deadlock)
        self.assertEqual(len(result.involved_processes), 2)
        self.assertIn("P1", result.involved_processes)
        self.assertIn("P2", result.involved_processes)
        self.assertEqual(result.cycle_path[0], result.cycle_path[-1])

    def test_four_resource_deadlock(self) -> None:
        """The canonical D1 circular wait across 4 processes and 4 resources."""
        rag = ResourceAllocationGraph(
            ["P1", "P2", "P3", "P4"],
            ["R1", "R2", "R3", "R4"],
        )
        # Assignments: R1->P1, R2->P2, R3->P3, R4->P4
        rag.grant_resource("P1", "R1")
        rag.grant_resource("P2", "R2")
        rag.grant_resource("P3", "R3")
        rag.grant_resource("P4", "R4")

        # Requests closing the ring: P1->R2, P2->R3, P3->R4, P4->R1
        rag.add_request("P1", "R2")
        rag.add_request("P2", "R3")
        rag.add_request("P3", "R4")
        rag.add_request("P4", "R1")

        result = DeadlockDetector.detect_cycle(rag)
        self.assertTrue(result.has_deadlock)
        self.assertEqual(len(result.involved_processes), 4)
        self.assertEqual(len(result.involved_resources), 4)
        self.assertEqual(set(result.involved_processes), {"P1", "P2", "P3", "P4"})
        self.assertEqual(set(result.involved_resources), {"R1", "R2", "R3", "R4"})

        formatted = result.format_cycle_path()
        self.assertIn("(P1)", formatted)
        self.assertIn("[R2]", formatted)
        self.assertIn("->", formatted)

    def test_deadlock_with_unrelated_branch(self) -> None:
        """A 2-process cycle exists alongside an innocent independent process."""
        rag = ResourceAllocationGraph(["P1", "P2", "P3"], ["R1", "R2", "R3"])
        # Cycle between P1 and P2
        rag.grant_resource("P1", "R1")
        rag.grant_resource("P2", "R2")
        rag.add_request("P1", "R2")
        rag.add_request("P2", "R1")

        # Innocent P3 holding R3
        rag.grant_resource("P3", "R3")

        result = DeadlockDetector.detect_cycle(rag)
        self.assertTrue(result.has_deadlock)
        self.assertNotIn("P3", result.involved_processes)
        self.assertNotIn("R3", result.involved_resources)


if __name__ == "__main__":
    unittest.main()

