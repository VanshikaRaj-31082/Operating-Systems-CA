"""
Unit tests for Deadlock Demonstration & Safe Recovery (src/workloads/deadlock_scenario.py).
"""

import unittest
from src.workloads.deadlock_scenario import DeadlockScenario, run_deadlock_trial


class TestDeadlockScenario(unittest.TestCase):

    def test_hierarchical_worker_completion(self) -> None:
        mgr = DeadlockScenario()
        mgr.event_start.set()
        c1 = mgr.hierarchical_worker(1, ops=50)
        c2 = mgr.hierarchical_worker(2, ops=50)
        self.assertEqual(c1, 50)
        self.assertEqual(c2, 50)

    def test_backoff_worker_completion(self) -> None:
        mgr = DeadlockScenario()
        mgr.event_start.set()
        c1, r1 = mgr.backoff_worker(1, ops=20, timeout_s=0.01)
        c2, r2 = mgr.backoff_worker(2, ops=20, timeout_s=0.01)
        self.assertEqual(c1, 20)
        self.assertEqual(c2, 20)
        self.assertGreaterEqual(r1, 0)
        self.assertGreaterEqual(r2, 0)

    def test_run_deadlock_trial_circular_watchdog_safety(self) -> None:
        # Watchdog must detect deadlock within timeout without hanging process
        res = run_deadlock_trial(
            scenario="circular_deadlock_unmitigated",
            watchdog_timeout_s=0.3,
            ops=10
        )
        self.assertTrue(res["deadlock_observed"])
        self.assertTrue(res["watchdog_triggered"])
        self.assertEqual(res["status"], "deadlock_detected_and_safely_mitigated")
        self.assertIn("thread_states_during_incident", res)

    def test_run_deadlock_trial_hierarchy_avoidance(self) -> None:
        res = run_deadlock_trial(
            scenario="lock_hierarchy_avoidance",
            watchdog_timeout_s=1.0,
            ops=20
        )
        self.assertFalse(res["deadlock_observed"])
        self.assertFalse(res["watchdog_triggered"])
        self.assertEqual(res["operations_completed"], 40)
        self.assertEqual(res["status"], "avoidance_success_zero_deadlocks")

    def test_run_deadlock_trial_backoff_recovery(self) -> None:
        res = run_deadlock_trial(
            scenario="trylock_exponential_backoff_recovery",
            watchdog_timeout_s=1.5,
            ops=20
        )
        self.assertFalse(res["deadlock_observed"])
        self.assertFalse(res["watchdog_triggered"])
        self.assertEqual(res["operations_completed"], 40)
        self.assertEqual(res["status"], "recovery_success_with_backoff")


if __name__ == "__main__":
    unittest.main()
