"""Unit tests for Resource model and Resource Allocation Graph (RAG)."""

from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESS_WORKFLOWS, RESOURCES
from src.models import EdgeType, ProcessState, Resource, ResourceAllocationGraph


class TestResourceModel(unittest.TestCase):
    """Tests for the Resource primitive."""

    def test_resource_initialization(self) -> None:
        res = Resource("R1", "Printer", 1)
        self.assertEqual(res.id, "R1")
        self.assertEqual(res.name, "Printer")
        self.assertEqual(res.rank, 1)
        self.assertIsNone(res.current_owner)

    def test_acquire_and_release(self) -> None:
        res = Resource("R1", "Printer", 1)
        self.assertTrue(res.acquire("P1", blocking=True, timeout=1.0))
        self.assertEqual(res.current_owner, "P1")

        # Second acquire should fail with non-blocking or timeout
        self.assertFalse(res.acquire("P2", blocking=False))

        res.release("P1")
        self.assertIsNone(res.current_owner)

        # Now P2 can acquire
        self.assertTrue(res.acquire("P2", blocking=True, timeout=1.0))
        self.assertEqual(res.current_owner, "P2")
        res.release("P2")

    def test_invalid_release_raises_error(self) -> None:
        res = Resource("R1", "Printer", 1)
        res.acquire("P1")
        with self.assertRaises(RuntimeError):
            res.release("P2")  # P2 does not own R1
        res.release("P1")


class TestResourceAllocationGraph(unittest.TestCase):
    """Tests for thread-safe bipartite Resource Allocation Graph."""

    def setUp(self) -> None:
        self.rag = ResourceAllocationGraph(
            process_ids=list(PROCESS_WORKFLOWS.keys()),
            resource_ids=list(RESOURCES.keys()),
        )

    def test_edge_lifecycle(self) -> None:
        # P1 requests R1
        self.rag.add_request("P1", "R1")
        adj = self.rag.get_adjacency_copy()
        self.assertIn("R1", adj["P1"])
        self.assertNotIn("P1", adj["R1"])

        # R1 is granted to P1: converts request P1->R1 into assignment R1->P1
        self.rag.grant_resource("P1", "R1")
        adj = self.rag.get_adjacency_copy()
        self.assertNotIn("R1", adj["P1"])
        self.assertIn("P1", adj["R1"])

        # P1 releases R1: removes assignment R1->P1
        self.rag.release_resource("P1", "R1")
        adj = self.rag.get_adjacency_copy()
        self.assertNotIn("P1", adj["R1"])

    def test_concurrent_graph_mutations(self) -> None:
        """Verify thread-safety of graph modifications under concurrent access."""
        errors: list[Exception] = []

        def worker(pid: str, rid: str) -> None:
            try:
                for _ in range(50):
                    self.rag.add_request(pid, rid)
                    self.rag.grant_resource(pid, rid)
                    self.rag.release_resource(pid, rid)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(f"P{i}", f"R{i}"))
            for i in range(1, 5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        self.assertEqual(len(errors), 0, f"Concurrent mutation errors: {errors}")


if __name__ == "__main__":
    unittest.main()

