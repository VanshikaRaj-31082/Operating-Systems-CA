"""
Lock Contention and Scalability Investigation Module.
Complies with CA5 Official Challenge L16 (Lock Contention Investigation) and L9.
Measures execution time, throughput (ops/sec), and kernel context switches via /proc
across scaling thread counts under coarse, chunked, and partitioned locking.
"""

import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.proc_explorer import ContextSwitchTracker, ProcExplorer


class ContentionWorkload:
    """Implements three locking architectures: Coarse, Chunked, and Partitioned."""

    def __init__(self, num_stripes: int = 16) -> None:
        self.global_counter = 0
        self.global_lock = threading.Lock()

        self.num_stripes = num_stripes
        self.striped_counters = [0] * num_stripes
        self.striped_locks = [threading.Lock() for _ in range(num_stripes)]

    def run_coarse(self, thread_id: int, total_ops_for_thread: int) -> None:
        """Coarse-grained: acquires global mutex for every single increment."""
        for _ in range(total_ops_for_thread):
            with self.global_lock:
                self.global_counter += 1

    def run_chunked(self, thread_id: int, total_ops_for_thread: int, chunk_size: int = 10) -> None:
        """
        Engineering Intervention 1 (Batching):
        Accumulates operations locally and updates the global counter in chunks,
        reducing lock acquisition frequency by a factor of chunk_size.
        """
        remaining = total_ops_for_thread
        while remaining > 0:
            batch = min(remaining, chunk_size)
            with self.global_lock:
                self.global_counter += batch
            remaining -= batch

    def run_partitioned(self, thread_id: int, total_ops_for_thread: int) -> None:
        """
        Engineering Intervention 2 (Partitioned / Striped Locking):
        Assigns each thread to an independent stripe with its own lock,
        eliminating cross-thread lock contention.
        """
        stripe_idx = thread_id % self.num_stripes
        lock = self.striped_locks[stripe_idx]
        for _ in range(total_ops_for_thread):
            with lock:
                self.striped_counters[stripe_idx] += 1


def run_contention_trial(
    thread_count: int,
    total_ops: int,
    strategy: str = "coarse_mutex",
    chunk_size: int = 10,
    explorer: Optional[ProcExplorer] = None
) -> Dict[str, Any]:
    """
    Executes a controlled contention trial, tracking:
    - Wall-clock execution time
    - Throughput (ops/second)
    - Voluntary context switches (threads blocked on futex)
    - Non-voluntary context switches (preemption by kernel scheduler)
    """
    valid_strategies = ("coarse_mutex", "chunked_mutex", "partitioned_striped")
    if strategy not in valid_strategies:
        raise ValueError(f"Unknown strategy: '{strategy}'. Must be one of {valid_strategies}")

    ops_per_thread = total_ops // thread_count
    actual_total_ops = ops_per_thread * thread_count
    workload = ContentionWorkload(num_stripes=max(thread_count, 16))

    tracker = ContextSwitchTracker(pid=os.getpid(), explorer=explorer)

    def worker(tid: int) -> None:
        if strategy == "coarse_mutex":
            workload.run_coarse(tid, ops_per_thread)
        elif strategy == "chunked_mutex":
            workload.run_chunked(tid, ops_per_thread, chunk_size=chunk_size)
        elif strategy == "partitioned_striped":
            workload.run_partitioned(tid, ops_per_thread)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    threads = [
        threading.Thread(target=worker, args=(i,), name=f"ContentionWorker-{i}")
        for i in range(thread_count)
    ]

    tracker.start()
    start_time = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration_s = time.perf_counter() - start_time
    delta_vol, delta_nonvol = tracker.stop()

    if strategy == "partitioned_striped":
        observed_total = sum(workload.striped_counters)
    else:
        observed_total = workload.global_counter

    throughput = (actual_total_ops / duration_s) if duration_s > 0 else 0.0

    return {
        "thread_count": thread_count,
        "strategy": strategy,
        "chunk_size": chunk_size if strategy == "chunked_mutex" else 1,
        "total_ops_planned": actual_total_ops,
        "total_ops_observed": observed_total,
        "duration_s": duration_s,
        "throughput_ops_sec": throughput,
        "voluntary_ctxt_switches": delta_vol,
        "nonvoluntary_ctxt_switches": delta_nonvol,
        "total_ctxt_switches": delta_vol + delta_nonvol,
    }


if __name__ == "__main__":
    import json
    for strat in ["coarse_mutex", "chunked_mutex", "partitioned_striped"]:
        res = run_contention_trial(thread_count=4, total_ops=200000, strategy=strat, chunk_size=10)
        print(f"Strategy: {strat}")
        print(json.dumps(res, indent=2))
