"""
Race Condition Demonstration and Correction Module.
Complies with CA5 Official Challenge L10 (Race Condition and Correction).
Demonstrates shared-state corruption under concurrent thread execution
and validates absolute correctness when synchronized with mutual exclusion.
"""

import threading
import time
from typing import Any, Dict, List, Tuple


class SharedAccount:
    """Represents a shared monetary balance or shared memory counter."""

    def __init__(self, initial_balance: int = 0) -> None:
        self.balance: int = initial_balance
        self._lock = threading.Lock()

    def deposit_unsynchronized(self, amount: int = 1) -> None:
        """
        Unsynchronized read-modify-write operation.
        Calls time.sleep(0) (POSIX sched_yield) between read and store to simulate
        interleaving and thread preemption, reliably triggering lost updates.
        """
        current = self.balance
        time.sleep(0)  # Forces Linux thread context switch (sched_yield)
        self.balance = current + amount

    def deposit_synchronized(self, amount: int = 1) -> None:
        """
        POSIX/Python Mutex synchronized critical section.
        Guarantees atomicity and mutual exclusion even across preemption points.
        """
        with self._lock:
            current = self.balance
            time.sleep(0)
            self.balance = current + amount


def run_race_trial(
    thread_count: int,
    ops_per_thread: int,
    synchronized: bool = False
) -> Dict[str, Any]:
    """
    Executes a single trial of the race condition experiment.
    Measures elapsed wall-clock time, expected vs observed balance, and error.
    """
    account = SharedAccount(initial_balance=0)
    expected_total = thread_count * ops_per_thread

    def worker() -> None:
        if synchronized:
            for _ in range(ops_per_thread):
                account.deposit_synchronized(1)
        else:
            for _ in range(ops_per_thread):
                account.deposit_unsynchronized(1)

    threads: List[threading.Thread] = [
        threading.Thread(target=worker, name=f"Worker-{i}")
        for i in range(thread_count)
    ]

    start_time = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration_s = time.perf_counter() - start_time

    observed_total = account.balance
    discrepancy = expected_total - observed_total
    relative_error = (discrepancy / expected_total) if expected_total > 0 else 0.0

    return {
        "thread_count": thread_count,
        "ops_per_thread": ops_per_thread,
        "synchronized": synchronized,
        "expected_balance": expected_total,
        "observed_balance": observed_total,
        "discrepancy": discrepancy,
        "relative_error": relative_error,
        "duration_s": duration_s,
        "throughput_ops_sec": (expected_total / duration_s) if duration_s > 0 else 0.0,
    }


if __name__ == "__main__":
    print("Testing Unsynchronized Race:")
    res_unsync = run_race_trial(thread_count=4, ops_per_thread=100000, synchronized=False)
    print(res_unsync)
    print("\nTesting Synchronized Mutex:")
    res_sync = run_race_trial(thread_count=4, ops_per_thread=100000, synchronized=True)
    print(res_sync)
