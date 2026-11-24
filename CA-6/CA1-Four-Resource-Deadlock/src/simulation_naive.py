"""Deterministic Naive Deadlock Simulation.

Demonstrates the unconstrained, circular-wait deadlock scenario across 4 processes
and 4 resources using synchronization barriers for 100% deterministic reproducibility.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from src.config import (
    BARRIER_TIMEOUT_SECONDS,
    DEADLOCK_TIMEOUT_SECONDS,
    PROCESS_WORKFLOWS,
    RESOURCES,
    WORK_DURATION_SECONDS,
)
from src.deadlock_detector import CycleDetectionResult, DeadlockDetector
from src.models import ProcessInfo, ProcessState, Resource, ResourceAllocationGraph


class NaiveSimulation:
    """Manages the unconstrained, circular resource acquisition simulation."""

    def __init__(self, lock_timeout: Optional[float] = 3.0) -> None:
        self.lock_timeout = lock_timeout
        self.resources: Dict[str, Resource] = {
            rid: Resource(rid, rcfg.name, rcfg.rank)
            for rid, rcfg in RESOURCES.items()
        }
        self.rag = ResourceAllocationGraph(
            process_ids=list(PROCESS_WORKFLOWS.keys()),
            resource_ids=list(RESOURCES.keys()),
        )
        self.processes: Dict[str, ProcessInfo] = {
            pid: ProcessInfo(id=pid, name=pw.name)
            for pid, pw in PROCESS_WORKFLOWS.items()
        }
        self.barrier = threading.Barrier(parties=len(PROCESS_WORKFLOWS))
        self.log_messages: List[str] = []
        self._log_lock = threading.Lock()
        self.start_time: float = 0.0
        self.threads: List[threading.Thread] = []
        self.detection_result: Optional[CycleDetectionResult] = None
        self._stopped = False

    def log(self, message: str) -> None:
        """Thread-safe timestamped logging."""
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0.0
        entry = f"[{elapsed:6.3f}s] {message}"
        with self._log_lock:
            self.log_messages.append(entry)

    def _worker(self, pid: str) -> None:
        workflow = PROCESS_WORKFLOWS[pid]
        p_info = self.processes[pid]
        p_info.start_time = time.time()
        p_info.state = ProcessState.INITIALIZING

        first_res_id, second_res_id = workflow.naive_order
        res1 = self.resources[first_res_id]
        res2 = self.resources[second_res_id]

        try:
            # Step 1: Acquire first resource
            self.log(f"[{pid}: {p_info.name}] Requesting first resource [{first_res_id}: {res1.name}] (Rank {res1.rank})...")
            self.rag.add_request(pid, first_res_id)
            acquired_first = res1.acquire(pid, blocking=True, timeout=self.lock_timeout)

            if not acquired_first:
                p_info.state = ProcessState.DEADLOCKED
                self.log(f"[{pid}] Timed out waiting for first resource [{first_res_id}]")
                return

            self.rag.grant_resource(pid, first_res_id)
            p_info.held_resources.append(first_res_id)
            p_info.state = ProcessState.HOLDING
            self.log(f"[{pid}] Acquired [{first_res_id}: {res1.name}]. Now holding: {p_info.held_resources}")

            # Step 2: Rendezvous at the barrier so ALL 4 processes hold their first resource
            self.log(f"[{pid}] Waiting at synchronization barrier for other processes...")
            self.barrier.wait(timeout=BARRIER_TIMEOUT_SECONDS)

            # Step 3: Request second resource (creates circular wait)
            p_info.state = ProcessState.WAITING
            p_info.waiting_for = second_res_id
            self.rag.add_request(pid, second_res_id)
            self.log(
                f"[{pid}] Requesting second resource [{second_res_id}: {res2.name}] (Rank {res2.rank}) ... "
                f"WAITING (Held by {res2.current_owner})"
            )

            timeout_val = self.lock_timeout if self.lock_timeout is not None else -1
            acquired_second = res2.acquire(pid, blocking=True, timeout=timeout_val)

            if acquired_second:
                # This branch is only reachable if no circular wait occurs (e.g. non-circular test)
                self.rag.grant_resource(pid, second_res_id)
                p_info.held_resources.append(second_res_id)
                p_info.waiting_for = None
                p_info.state = ProcessState.EXECUTING
                self.log(f"[{pid}] Acquired second resource [{second_res_id}]. Performing work...")
                time.sleep(WORK_DURATION_SECONDS)

                # Release resources in reverse order
                res2.release(pid)
                self.rag.release_resource(pid, second_res_id)
                res1.release(pid)
                self.rag.release_resource(pid, first_res_id)
                p_info.held_resources.clear()
                p_info.state = ProcessState.COMPLETED
                p_info.finish_time = time.time()
                self.log(f"[{pid}] Finished work and released all resources.")
            else:
                # Expected in deadlock: acquire timed out
                p_info.state = ProcessState.DEADLOCKED
                self.log(f"[{pid}] Lock acquire timed out on [{second_res_id}]. Process DEADLOCKED.")

        except threading.BrokenBarrierError:
            self.log(f"[{pid}] Synchronization barrier broken.")
            p_info.error_message = "Barrier broken"
        except Exception as e:
            self.log(f"[{pid}] Unexpected error: {e}")
            p_info.error_message = str(e)

    def run(self, monitor_delay: float = 0.5) -> CycleDetectionResult:
        """Execute the naive simulation and detect the circular wait deadlock."""
        self.start_time = time.time()
        self.log("=== STARTING NAIVE FOUR-RESOURCE SIMULATION (DETERMINISTIC DEADLOCK) ===")

        # Launch all 4 threads
        for pid in PROCESS_WORKFLOWS:
            t = threading.Thread(target=self._worker, args=(pid,), name=f"Thread-{pid}")
            self.threads.append(t)
            t.start()

        # Wait briefly for all threads to pass the barrier and block on second resource
        time.sleep(monitor_delay)

        # Run cycle detection on the live RAG
        self.log("Running cycle detection on active Resource Allocation Graph...")
        self.detection_result = DeadlockDetector.detect_cycle(self.rag)

        if self.detection_result.has_deadlock:
            self.log(f"[ALERT] DEADLOCK DETECTED! Cycle: {self.detection_result.format_cycle_path()}")
            for pid, p in self.processes.items():
                if p.state == ProcessState.WAITING:
                    p.state = ProcessState.DEADLOCKED
        else:
            self.log("No deadlock detected at inspection time.")

        # Wait for threads to finish or time out
        for t in self.threads:
            t.join(timeout=self.lock_timeout or 3.0)

        self.log("=== NAIVE SIMULATION RUN COMPLETED ===")
        return self.detection_result

