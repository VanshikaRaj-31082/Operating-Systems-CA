"""
Unit tests for Race Condition & Correction Workload (src/workloads/race_condition.py).
"""

import unittest
from src.workloads.race_condition import SharedAccount, run_race_trial


class TestRaceCondition(unittest.TestCase):

    def test_shared_account_single_thread(self) -> None:
        account = SharedAccount(initial_balance=10)
        account.deposit_synchronized(5)
        self.assertEqual(account.balance, 15)
        account.deposit_unsynchronized(5)
        self.assertEqual(account.balance, 20)

    def test_synchronized_execution_exact_correctness(self) -> None:
        # Multi-threaded synchronized trial must produce zero discrepancy
        res = run_race_trial(thread_count=4, ops_per_thread=5000, synchronized=True)
        self.assertEqual(res["discrepancy"], 0)
        self.assertEqual(res["relative_error"], 0.0)
        self.assertEqual(res["observed_balance"], res["expected_balance"])
        self.assertGreater(res["duration_s"], 0.0)
        self.assertGreater(res["throughput_ops_sec"], 0.0)

    def test_run_race_trial_schema(self) -> None:
        res = run_race_trial(thread_count=2, ops_per_thread=1000, synchronized=False)
        self.assertIn("thread_count", res)
        self.assertIn("ops_per_thread", res)
        self.assertIn("synchronized", res)
        self.assertIn("expected_balance", res)
        self.assertIn("observed_balance", res)
        self.assertIn("discrepancy", res)
        self.assertIn("relative_error", res)
        self.assertIn("duration_s", res)
        self.assertIn("throughput_ops_sec", res)


if __name__ == "__main__":
    unittest.main()
