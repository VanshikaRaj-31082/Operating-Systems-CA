"""
CA-3 Phase 4: Automated Verification Test Suite
Tests for Hierarchical Resource Ordering (src/deadlock_prevented.py)

Validates:
1. Both threads complete successfully.
2. No thread remains blocked after the timeout.
3. Both threads follow the same lock acquisition order (Lock A -> Lock B).
4. Repeated concurrent execution across at least 100 iterations with 0 deadlocks.
5. Shared critical-section data integrity under concurrent contention.
6. Exception safety and automatic lock release via LIFO context managers.
"""

import sys
import time
import threading
import unittest
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from deadlock_prevented import run_prevented_deadlock


class TestDeadlockPrevention(unittest.TestCase):
    """Unit tests for the Hierarchical Resource Ordering deadlock remediation."""

    def test_both_threads_complete_successfully(self):
        """Test that both Thread 1 and Thread 2 complete normally without blocking."""
        result = run_prevented_deadlock(timeout=2.0)
        self.assertTrue(result["thread_1_completed"], "Thread 1 should complete successfully")
        self.assertTrue(result["thread_2_completed"], "Thread 2 should complete successfully")
        self.assertTrue(result["both_completed"], "Both threads should complete without deadlock")
        self.assertIsNone(result["error"], f"Unexpected error during execution: {result['error']}")

    def test_no_thread_remains_blocked_after_timeout(self):
        """Test that neither thread is alive or hanging after execution completes."""
        start_time = time.perf_counter()
        result = run_prevented_deadlock(timeout=2.0)
        elapsed = time.perf_counter() - start_time

        self.assertTrue(result["both_completed"], "Both threads must finish")
        # Ensure completion is fast and did not hit the 2.0s watchdog boundary
        self.assertLess(elapsed, 1.0, f"Execution took {elapsed:.4f}s, expected < 1.0s")

    def test_both_threads_follow_same_acquisition_order(self):
        """
        Verify that both Thread 1 and Thread 2 follow the exact same global order:
        Lock A is acquired BEFORE Lock B.
        """
        trace = []
        result = run_prevented_deadlock(timeout=2.0, execution_trace=trace)
        self.assertTrue(result["both_completed"])

        # Check Thread 1 ordering
        t1_acquired_a = [i for i, ev in enumerate(trace) if ev == "T1:Acquired_A"]
        t1_acquired_b = [i for i, ev in enumerate(trace) if ev == "T1:Acquired_B"]
        self.assertTrue(len(t1_acquired_a) > 0 and len(t1_acquired_b) > 0)
        self.assertLess(t1_acquired_a[0], t1_acquired_b[0], "T1 must acquire Lock A before Lock B")

        # Check Thread 2 ordering
        t2_acquired_a = [i for i, ev in enumerate(trace) if ev == "T2:Acquired_A"]
        t2_acquired_b = [i for i, ev in enumerate(trace) if ev == "T2:Acquired_B"]
        self.assertTrue(len(t2_acquired_a) > 0 and len(t2_acquired_b) > 0)
        self.assertLess(t2_acquired_a[0], t2_acquired_b[0], "T2 must acquire Lock A before Lock B")

    def test_repeated_concurrent_execution_100_iterations(self):
        """
        Stress test: Execute 100 consecutive concurrent runs.
        Verify 0% deadlock rate (100 / 100 successful completions).
        """
        total_runs = 100
        successful_runs = 0
        total_time = 0.0

        for i in range(total_runs):
            # Short timeout of 1.0s per iteration ensures tests fail quickly if deadlocked
            result = run_prevented_deadlock(timeout=1.0)
            if result["both_completed"]:
                successful_runs += 1
            total_time += result["execution_time_sec"]

        self.assertEqual(
            successful_runs,
            total_runs,
            f"Expected {total_runs} successful runs, but got {successful_runs}."
        )
        avg_time = total_time / total_runs
        print(f"\n[STRESS TEST] 100 iterations completed: 100% success. Avg duration: {avg_time*1000:.3f} ms")

    def test_shared_critical_section_integrity(self):
        """
        Verify that shared data is correctly protected and race-free.
        Both threads increment a shared counter across multiple iterations.
        """
        shared_counter = [0]
        iterations = 50
        expected_total = iterations * 2  # Each thread increments 50 times

        result = run_prevented_deadlock(
            timeout=2.0,
            shared_counter=shared_counter,
            iterations_per_thread=iterations,
            simulate_work=False
        )

        self.assertTrue(result["both_completed"])
        self.assertEqual(
            shared_counter[0],
            expected_total,
            f"Race condition detected! Shared counter is {shared_counter[0]}, expected {expected_total}."
        )

    def test_correct_lock_release_on_exception(self):
        """
        Verify that if an unhandled exception occurs inside the critical section,
        both Lock A and Lock B are safely released by the context manager
        and are immediately available to other threads.
        """
        lock_a = threading.Lock()
        lock_b = threading.Lock()

        # Thread that raises an exception inside the nested lock
        def failing_worker():
            try:
                with lock_a:
                    with lock_b:
                        raise ValueError("Simulated unexpected failure inside critical section")
            except ValueError:
                pass

        t = threading.Thread(target=failing_worker)
        t.start()
        t.join(timeout=1.0)

        # Verify that Lock B and Lock A are both fully unlocked
        acquired_a = lock_a.acquire(blocking=False)
        self.assertTrue(acquired_a, "Lock A must be released even after an exception")
        if acquired_a:
            lock_a.release()

        acquired_b = lock_b.acquire(blocking=False)
        self.assertTrue(acquired_b, "Lock B must be released even after an exception")
        if acquired_b:
            lock_b.release()

    def test_reverse_order_release_lifo(self):
        """
        Verify that locks are released in exact reverse order of acquisition:
        Acquire A -> Acquire B -> Release B -> Release A.
        """
        trace = []
        result = run_prevented_deadlock(timeout=2.0, execution_trace=trace)
        self.assertTrue(result["both_completed"])

        # Check for Thread 1
        t1_rel_b = [i for i, ev in enumerate(trace) if ev == "T1:Releasing_B"]
        t1_rel_a = [i for i, ev in enumerate(trace) if ev == "T1:Releasing_A"]
        self.assertTrue(len(t1_rel_b) > 0 and len(t1_rel_a) > 0)
        self.assertLess(t1_rel_b[0], t1_rel_a[0], "T1 must release Lock B before Lock A")

        # Check for Thread 2
        t2_rel_b = [i for i, ev in enumerate(trace) if ev == "T2:Releasing_B"]
        t2_rel_a = [i for i, ev in enumerate(trace) if ev == "T2:Releasing_A"]
        self.assertTrue(len(t2_rel_b) > 0 and len(t2_rel_a) > 0)
        self.assertLess(t2_rel_b[0], t2_rel_a[0], "T2 must release Lock B before Lock A")


if __name__ == "__main__":
    unittest.main()
