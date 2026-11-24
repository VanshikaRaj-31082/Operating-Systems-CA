"""Automated stress test verifying deadlock-free execution under Global Resource Ordering."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation_prevented import PreventedSimulation


class TestDeadlockPrevention(unittest.TestCase):
    """Stress testing the resource-ordering prevention protocol."""

    def test_single_prevented_run(self) -> None:
        """Verify that a single prevented simulation completes all tasks with zero cycles."""
        sim = PreventedSimulation()
        metrics = sim.run()

        self.assertEqual(metrics["completed_tasks"], 4)
        self.assertEqual(metrics["total_tasks"], 4)
        self.assertEqual(metrics["cycles_detected"], 0)
        self.assertTrue(metrics["all_completed"])

    def test_repeated_stress_prevented_runs(self) -> None:
        """Run 20 consecutive stress executions.

        Verifies that across repeated concurrent runs, deadlock is 100% prevented,
        no cycles occur, and all tasks finish within bounded timeouts.
        """
        num_iterations = 20
        total_completed = 0
        total_cycles = 0

        for i in range(num_iterations):
            sim = PreventedSimulation()
            metrics = sim.run()

            self.assertEqual(
                metrics["completed_tasks"],
                4,
                f"Iteration {i+1} failed to complete all tasks",
            )
            self.assertEqual(
                metrics["cycles_detected"],
                0,
                f"Iteration {i+1} detected an impossible cycle!",
            )
            total_completed += int(metrics["completed_tasks"])
            total_cycles += int(metrics["cycles_detected"])

        self.assertEqual(total_completed, num_iterations * 4)
        self.assertEqual(total_cycles, 0)


if __name__ == "__main__":
    unittest.main()

