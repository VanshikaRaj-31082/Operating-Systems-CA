"""Deadlock-Prevented Simulation using Global Resource Ordering.

Enforces Havender's Total Ordering principle (strictly increasing resource ranks)
to eliminate the Circular Wait condition. Guarantees deadlock-free execution.
Note: While resource ordering eliminates deadlock, it does not inherently guarantee
starvation-freedom unless accompanied by fair queueing.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from src.config import (
    PROCESS_WORKFLOWS,
    RESOURCES,
    WORK_DURATION_SECONDS,
)
from src.deadlock_detector import CycleDetectionResult, DeadlockDetector
from src.models import ProcessInfo, ProcessState, Resource, ResourceAllocationGraph


class PreventedSimulation:
    """Manages resource acquisition enforced by strict global resource ordering."""

    def __init__(self) -> None:
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
        self.log_messages: List[str] = []
        self._log_lock = threading.Lock()
        self.start_time: float = 0.0
        self.threads: List[threading.Thread] = []
        self.cycles_detected_during_run: int = 0
        self.completed_count: int = 0
        self._completed_lock = threading.Lock()

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

        # Enforce Hierarchical Resource Ordering:
        # Instead of naive order, use strictly increasing rank order:
        first_res_id, second_res_id = workflow.prevented_order
        res1 = self.resources[first_res_id]
        res2 = self.resources[second_res_id]

        # Verify hierarchical invariant: rank(first) < rank(second)
        if res1.rank >= res2.rank:
            raise ValueError(
                f"Protocol violation for {pid}: rank({res1.id})={res1.rank} "
                f"must be strictly less than rank({res2.id})={res2.rank}"
            )

        if workflow.naive_order != workflow.prevented_order:
            self.log(
                f"[{pid}: {p_info.name}] Protocol re-ordered requests: "
                f"Naive {workflow.naive_order} -> Hierarchical {workflow.prevented_order} "
                f"(Rank {res1.rank} < Rank {res2.rank})"
            )

        try:
            # Step 1: Acquire lower-ranked resource first
            self.log(f"[{pid}] Requesting [{first_res_id}: {res1.name}] (Rank {res1.rank})...")
            self.rag.add_request(pid, first_res_id)
            p_info.state = ProcessState.WAITING
            p_info.waiting_for = first_res_id

            res1.acquire(pid, blocking=True)
            self.rag.grant_resource(pid, first_res_id)
            p_info.held_resources.append(first_res_id)
            p_info.waiting_for = None
            p_info.state = ProcessState.HOLDING
            self.log(f"[{pid}] Acquired [{first_res_id}: {res1.name}] (Rank {res1.rank}).")

            # Intermediate audit check on RAG for cycles
            check = DeadlockDetector.detect_cycle(self.rag)
            if check.has_deadlock:
                self.cycles_detected_during_run += 1

            # Step 2: Acquire higher-ranked resource second
            self.log(f"[{pid}] Requesting [{second_res_id}: {res2.name}] (Rank {res2.rank})...")
            self.rag.add_request(pid, second_res_id)
            p_info.state = ProcessState.WAITING
            p_info.waiting_for = second_res_id

            res2.acquire(pid, blocking=True)
            self.rag.grant_resource(pid, second_res_id)
            p_info.held_resources.append(second_res_id)
            p_info.waiting_for = None
            p_info.state = ProcessState.EXECUTING
            self.log(f"[{pid}] Acquired [{second_res_id}: {res2.name}] (Rank {res2.rank}). All needed resources secured!")

            # Step 3: Perform simulated work
            self.log(f"[{pid}] Processing transaction with {p_info.held_resources}...")
            time.sleep(WORK_DURATION_SECONDS)

            # Step 4: Release resources in reverse order
            res2.release(pid)
            self.rag.release_resource(pid, second_res_id)
            res1.release(pid)
            self.rag.release_resource(pid, first_res_id)
            p_info.held_resources.clear()

            p_info.state = ProcessState.COMPLETED
            p_info.finish_time = time.time()
            self.log(f"[{pid}] Released all resources. Completed in {p_info.elapsed_time:.3f}s.")

            with self._completed_lock:
                self.completed_count += 1

        except Exception as e:
            self.log(f"[{pid}] Error in worker: {e}")
            p_info.error_message = str(e)

    def run(self) -> Dict[str, object]:
        """Execute the prevented simulation and return full operational metrics."""
        self.start_time = time.time()
        self.log("=== STARTING PREVENTED FOUR-RESOURCE SIMULATION (GLOBAL RESOURCE ORDERING) ===")

        # Launch all 4 threads
        for pid in PROCESS_WORKFLOWS:
            t = threading.Thread(target=self._worker, args=(pid,), name=f"Thread-Prevented-{pid}")
            self.threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in self.threads:
            t.join(timeout=10.0)

        total_elapsed = time.time() - self.start_time
        final_rag_check = DeadlockDetector.detect_cycle(self.rag)
        if final_rag_check.has_deadlock:
            self.cycles_detected_during_run += 1

        self.log(
            f"=== PREVENTED SIMULATION COMPLETED: {self.completed_count}/{len(PROCESS_WORKFLOWS)} "
            f"tasks finished in {total_elapsed:.3f}s (Cycles: {self.cycles_detected_during_run}) ==="
        )

        return {
            "completed_tasks": self.completed_count,
            "total_tasks": len(PROCESS_WORKFLOWS),
            "total_elapsed_seconds": total_elapsed,
            "cycles_detected": self.cycles_detected_during_run,
            "all_completed": self.completed_count == len(PROCESS_WORKFLOWS),
        }

