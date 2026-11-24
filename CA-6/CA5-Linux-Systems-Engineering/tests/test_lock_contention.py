"""
Unit tests for Lock Contention & Context Switch Tracking (src/workloads/lock_contention.py).
"""

import unittest
from src.workloads.lock_contention import ContentionWorkload, run_contention_trial


class TestLockContention(unittest.TestCase):

    def test_contention_workload_coarse(self) -> None:
        workload = ContentionWorkload()
        workload.run_coarse(thread_id=0, total_ops_for_thread=500)
        self.assertEqual(workload.global_counter, 500)

    def test_contention_workload_chunked(self) -> None:
        workload = ContentionWorkload()
        workload.run_chunked(thread_id=0, total_ops_for_thread=500, chunk_size=20)
        self.assertEqual(workload.global_counter, 500)

    def test_contention_workload_partitioned(self) -> None:
        workload = ContentionWorkload(num_stripes=4)
        workload.run_partitioned(thread_id=0, total_ops_for_thread=200)
        workload.run_partitioned(thread_id=1, total_ops_for_thread=300)
        self.assertEqual(sum(workload.striped_counters), 500)

    def test_run_contention_trial_coarse(self) -> None:
        res = run_contention_trial(thread_count=2, total_ops=2000, strategy="coarse_mutex")
        self.assertEqual(res["total_ops_observed"], res["total_ops_planned"])
        self.assertGreater(res["throughput_ops_sec"], 0.0)
        self.assertIn("voluntary_ctxt_switches", res)
        self.assertIn("nonvoluntary_ctxt_switches", res)

    def test_run_contention_trial_chunked(self) -> None:
        res = run_contention_trial(thread_count=2, total_ops=2000, strategy="chunked_mutex", chunk_size=10)
        self.assertEqual(res["total_ops_observed"], res["total_ops_planned"])
        self.assertEqual(res["chunk_size"], 10)

    def test_run_contention_trial_partitioned(self) -> None:
        res = run_contention_trial(thread_count=2, total_ops=2000, strategy="partitioned_striped")
        self.assertEqual(res["total_ops_observed"], res["total_ops_planned"])

    def test_invalid_strategy_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            run_contention_trial(thread_count=2, total_ops=100, strategy="nonexistent_strategy")


if __name__ == "__main__":
    unittest.main()
