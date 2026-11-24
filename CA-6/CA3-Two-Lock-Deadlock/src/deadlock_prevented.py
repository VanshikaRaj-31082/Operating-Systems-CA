"""
CA-3 Phase 4: Implementation of Hierarchical Resource Ordering
Remediates the Two-Lock Deadlock by enforcing a strict global acquisition order:
    Lock A (Index 1) -> Lock B (Index 2)
Both threads acquire Lock A first, then Lock B, and release in reverse order (Lock B then Lock A).
"""

import threading
import time
from typing import Dict, Any, List, Optional


def run_prevented_deadlock(
    timeout: float = 3.0,
    start_barrier: Optional[threading.Barrier] = None,
    execution_trace: Optional[List[str]] = None,
    shared_counter: Optional[List[int]] = None,
    iterations_per_thread: int = 1,
    simulate_work: bool = False
) -> Dict[str, Any]:
    """
    Executes two threads using Hierarchical Resource Ordering (Lock A -> Lock B).

    Args:
        timeout: Maximum duration to wait for each thread join in seconds.
        start_barrier: Optional 2-thread barrier to synchronize concurrent start before Lock A.
        execution_trace: Optional thread-safe list to log acquisition and release events.
        shared_counter: Optional list holding a single integer to verify critical section integrity.
        iterations_per_thread: Number of critical section entries per thread.
        simulate_work: Whether to insert small sleep intervals to stress concurrent interleavings.

    Returns:
        Dict containing execution metrics and completion status.
    """
    lock_a = threading.Lock()
    lock_b = threading.Lock()

    # Pre-acquisition synchronization: both threads start concurrently before Lock A
    if start_barrier is None:
        start_barrier = threading.Barrier(2)

    status = {
        "thread_1_completed": False,
        "thread_2_completed": False,
        "both_completed": False,
        "execution_time_sec": 0.0,
        "error": None
    }

    trace_lock = threading.Lock()

    def record_event(event: str):
        if execution_trace is not None:
            with trace_lock:
                execution_trace.append(event)

    def thread_1_worker():
        try:
            # Synchronize start so both threads race concurrently for Lock A
            start_barrier.wait(timeout=timeout)

            for _ in range(iterations_per_thread):
                record_event("T1:Requesting_A")
                with lock_a:  # Order 1: Acquire Lock A first
                    record_event("T1:Acquired_A")
                    if simulate_work:
                        time.sleep(0.001)

                    record_event("T1:Requesting_B")
                    with lock_b:  # Order 2: Acquire Lock B second
                        record_event("T1:Acquired_B")

                        # Critical Section: Mutate shared state safely
                        if shared_counter is not None:
                            current = shared_counter[0]
                            time.sleep(0.0001) if simulate_work else None
                            shared_counter[0] = current + 1

                        record_event("T1:Releasing_B")
                    # Lock B released in LIFO order upon exit of with lock_b
                    record_event("T1:Released_B")

                    record_event("T1:Releasing_A")
                # Lock A released in LIFO order upon exit of with lock_a
                record_event("T1:Released_A")

            status["thread_1_completed"] = True
        except Exception as e:
            status["error"] = f"Thread 1 exception: {e}"

    def thread_2_worker():
        try:
            # Synchronize start so both threads race concurrently for Lock A
            start_barrier.wait(timeout=timeout)

            for _ in range(iterations_per_thread):
                record_event("T2:Requesting_A")
                # CORRECTED ORDER: Thread 2 acquires Lock A first (Lock A < Lock B)
                with lock_a:  # Order 1: Acquire Lock A first
                    record_event("T2:Acquired_A")
                    if simulate_work:
                        time.sleep(0.001)

                    record_event("T2:Requesting_B")
                    with lock_b:  # Order 2: Acquire Lock B second
                        record_event("T2:Acquired_B")

                        # Critical Section: Mutate shared state safely
                        if shared_counter is not None:
                            current = shared_counter[0]
                            time.sleep(0.0001) if simulate_work else None
                            shared_counter[0] = current + 1

                        record_event("T2:Releasing_B")
                    # Lock B released in LIFO order upon exit of with lock_b
                    record_event("T2:Released_B")

                    record_event("T2:Releasing_A")
                # Lock A released in LIFO order upon exit of with lock_a
                record_event("T2:Released_A")

            status["thread_2_completed"] = True
        except Exception as e:
            status["error"] = f"Thread 2 exception: {e}"

    t1 = threading.Thread(target=thread_1_worker, name="Thread-1")
    t2 = threading.Thread(target=thread_2_worker, name="Thread-2")

    start_time = time.perf_counter()

    t1.start()
    t2.start()

    # Bounded joins to guarantee no infinite hang
    t1.join(timeout=timeout)
    t2.join(timeout=timeout)

    elapsed = time.perf_counter() - start_time
    status["execution_time_sec"] = elapsed

    # Verify neither thread is left hanging
    if not t1.is_alive() and not t2.is_alive():
        status["both_completed"] = status["thread_1_completed"] and status["thread_2_completed"]
    else:
        status["both_completed"] = False
        if t1.is_alive():
            status["error"] = "Thread 1 timed out and is still alive!"
        if t2.is_alive():
            status["error"] = "Thread 2 timed out and is still alive!"

    return status


def main():
    print("=" * 65)
    print("CA-3 Phase 4: Hierarchical Resource Ordering Demonstration")
    print("Global Order Enforced: Lock A -> Lock B for all threads")
    print("=" * 65)

    trace: List[str] = []
    counter = [0]

    result = run_prevented_deadlock(
        timeout=3.0,
        execution_trace=trace,
        shared_counter=counter,
        iterations_per_thread=1,
        simulate_work=True
    )

    print("\nExecution Trace:")
    for event in trace:
        print(f"  -> {event}")

    print(f"\nFinal Shared Counter Value: {counter[0]} (Expected: 2)")
    print(f"Execution Time: {result['execution_time_sec']:.6f} seconds")
    print(f"Thread 1 Completed: {result['thread_1_completed']}")
    print(f"Thread 2 Completed: {result['thread_2_completed']}")
    print(f"Both Completed (Deadlock Avoided): {result['both_completed']}")

    if result["both_completed"]:
        print("\nSUCCESS: Both threads completed without deadlock!")
    else:
        print(f"\nFAILURE: {result['error']}")


if __name__ == "__main__":
    main()
