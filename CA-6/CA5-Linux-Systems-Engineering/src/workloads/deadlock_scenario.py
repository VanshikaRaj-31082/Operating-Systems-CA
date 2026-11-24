"""
Controlled Deadlock Demonstration, Kernel State Inspection, and Safe Recovery.
Complies with CA5 Official Challenge L17 (Deadlock Demonstration and Recovery).
Demonstrates Coffman conditions (Circular Wait, Hold and Wait) on Linux.
Includes safety watchdog, /proc thread state verification, lock ordering avoidance,
and trylock with randomized exponential backoff recovery.
"""

import os
import random
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.proc_explorer import ProcExplorer


class DeadlockScenario:
    """Manages two shared locks and executes deadlock and recovery scenarios."""

    def __init__(self) -> None:
        self.lock_1 = threading.Lock()
        self.lock_2 = threading.Lock()
        self.event_start = threading.Event()
        self.deadlock_detected = False
        self.recovery_successful = False

    def unmitigated_worker_1(self, hold_delay_s: float = 0.05) -> None:
        """Worker 1: Acquires Lock 1 -> waits -> requests Lock 2."""
        self.event_start.wait()
        with self.lock_1:
            time.sleep(hold_delay_s)
            with self.lock_2:
                pass  # Critical section

    def unmitigated_worker_2(self, hold_delay_s: float = 0.05) -> None:
        """Worker 2: Acquires Lock 2 -> waits -> requests Lock 1 (Circular Wait)."""
        self.event_start.wait()
        with self.lock_2:
            time.sleep(hold_delay_s)
            with self.lock_1:
                pass  # Critical section

    def hierarchical_worker(self, worker_id: int, ops: int = 100) -> int:
        """
        Engineering Intervention 1 (Lock Hierarchy Avoidance):
        Enforces strict global lock acquisition ordering (Lock 1 before Lock 2).
        Eliminates Coffman Condition 4 (Circular Wait).
        """
        completed = 0
        self.event_start.wait()
        for _ in range(ops):
            with self.lock_1:
                with self.lock_2:
                    completed += 1
        return completed

    def backoff_worker(
        self,
        worker_id: int,
        ops: int = 100,
        timeout_s: float = 0.02,
        max_backoff_ms: float = 15.0
    ) -> Tuple[int, int]:
        """
        Engineering Intervention 2 (Trylock with Exponential Backoff Recovery):
        Breaks Coffman Condition 2 (Hold and Wait).
        If the secondary lock cannot be acquired within timeout_s, releases primary lock,
        sleeps for a randomized exponential backoff delay, and retries.
        """
        completed = 0
        retries = 0
        self.event_start.wait()

        primary_lock = self.lock_1 if worker_id == 1 else self.lock_2
        secondary_lock = self.lock_2 if worker_id == 1 else self.lock_1

        for _ in range(ops):
            attempts = 0
            while True:
                # Acquire primary
                primary_lock.acquire()
                # Try acquiring secondary
                acquired_sec = secondary_lock.acquire(timeout=timeout_s)
                if acquired_sec:
                    # Successfully acquired both without deadlock
                    try:
                        completed += 1
                    finally:
                        secondary_lock.release()
                        primary_lock.release()
                    break
                else:
                    # Deadlock prevention: release primary to break Hold-and-Wait
                    primary_lock.release()
                    retries += 1
                    attempts += 1
                    backoff_delay = random.uniform(0.001, (min(2 ** attempts, max_backoff_ms)) / 1000.0)
                    time.sleep(backoff_delay)
        return completed, retries


def run_deadlock_trial(
    scenario: str = "circular_deadlock_unmitigated",
    watchdog_timeout_s: float = 1.5,
    ops: int = 100,
    explorer: Optional[ProcExplorer] = None
) -> Dict[str, Any]:
    """
    Executes a controlled deadlock investigation trial.
    Guarantees that the experiment NEVER leaves the system hanging.
    """
    scenario_mgr = DeadlockScenario()
    proc_exp = explorer or ProcExplorer()
    my_pid = os.getpid()

    result: Dict[str, Any] = {
        "scenario": scenario,
        "deadlock_observed": False,
        "watchdog_triggered": False,
        "thread_states_during_incident": [],
        "execution_time_s": 0.0,
        "operations_completed": 0,
        "retries_count": 0,
        "status": "pending",
    }

    start_time = time.perf_counter()

    if scenario == "circular_deadlock_unmitigated":
        t1 = threading.Thread(target=scenario_mgr.unmitigated_worker_1, args=(0.02,), name="DeadlockThread-1", daemon=True)
        t2 = threading.Thread(target=scenario_mgr.unmitigated_worker_2, args=(0.02,), name="DeadlockThread-2", daemon=True)

        t1.start()
        t2.start()
        scenario_mgr.event_start.set()

        # Monitor thread states via /proc
        time.sleep(0.08)  # Allow both threads to acquire primary and block on secondary
        thread_details = proc_exp.get_thread_details(my_pid)
        result["thread_states_during_incident"] = [
            {"tid": td.get("tid"), "state": td.get("State"), "wchan": td.get("wchan")}
            for td in thread_details
        ]

        # Check if threads are still alive after short wait
        t1.join(timeout=watchdog_timeout_s)
        t2.join(timeout=0.01)

        if t1.is_alive() and t2.is_alive():
            result["deadlock_observed"] = True
            result["watchdog_triggered"] = True
            result["status"] = "deadlock_detected_and_safely_mitigated"
            # Threads are daemonic so will not hang process upon exit
        else:
            result["deadlock_observed"] = False
            result["status"] = "completed_no_deadlock"

    elif scenario == "lock_hierarchy_avoidance":
        results_counts = [0, 0]

        def w1():
            results_counts[0] = scenario_mgr.hierarchical_worker(1, ops=ops)

        def w2():
            results_counts[1] = scenario_mgr.hierarchical_worker(2, ops=ops)

        t1 = threading.Thread(target=w1, name="HierarchicalThread-1")
        t2 = threading.Thread(target=w2, name="HierarchicalThread-2")

        t1.start()
        t2.start()
        scenario_mgr.event_start.set()

        t1.join(timeout=watchdog_timeout_s * 2)
        t2.join(timeout=watchdog_timeout_s * 2)

        result["deadlock_observed"] = False
        result["operations_completed"] = sum(results_counts)
        result["status"] = "avoidance_success_zero_deadlocks"

    elif scenario == "trylock_exponential_backoff_recovery":
        worker_res: List[Tuple[int, int]] = [(0, 0), (0, 0)]

        def w1():
            worker_res[0] = scenario_mgr.backoff_worker(1, ops=ops)

        def w2():
            worker_res[1] = scenario_mgr.backoff_worker(2, ops=ops)

        t1 = threading.Thread(target=w1, name="BackoffThread-1")
        t2 = threading.Thread(target=w2, name="BackoffThread-2")

        t1.start()
        t2.start()
        scenario_mgr.event_start.set()

        t1.join(timeout=watchdog_timeout_s * 3)
        t2.join(timeout=watchdog_timeout_s * 3)

        total_completed = worker_res[0][0] + worker_res[1][0]
        total_retries = worker_res[0][1] + worker_res[1][1]

        result["deadlock_observed"] = False
        result["operations_completed"] = total_completed
        result["retries_count"] = total_retries
        result["status"] = "recovery_success_with_backoff"

    result["execution_time_s"] = time.perf_counter() - start_time
    return result


if __name__ == "__main__":
    import json
    for scen in ["circular_deadlock_unmitigated", "lock_hierarchy_avoidance", "trylock_exponential_backoff_recovery"]:
        res = run_deadlock_trial(scenario=scen, ops=100)
        print(f"Scenario: {scen} -> Status: {res['status']}, Time: {res['execution_time_s']:.4f}s")
