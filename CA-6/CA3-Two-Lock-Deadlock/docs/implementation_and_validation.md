# CA-3 Phase 4: Implementation and Validation Report
## Empirical Verification of Hierarchical Resource Ordering for Two-Lock Deadlock Remediation

**Course:** Operating Systems  
**Component:** Continuous Assessment 3 (10 Marks) – OS Design & Debugging Challenge  
**Category:** Category D – Deadlock  
**Challenge:** Challenge D1 – Two-Lock Deadlock  
**Primary Solution:** Hierarchical Resource Ordering ($\text{Lock A} < \text{Lock B}$)  
**Implementation File:** `src/deadlock_prevented.py`  
**Test Suite File:** `tests/test_deadlock_prevention.py`  
**Baseline File:** `src/deadlock_demo.py` (Preserved 100% Unmodified)  
**Execution Environment:** Windows 11 (64-bit) | Python 3.14.7  

---

## 1. Executive Summary

This report documents the implementation and experimental validation of **Hierarchical Resource Ordering** as the remediation for the two-lock deadlock in `src/deadlock_demo.py`. 

The original defective implementation (`deadlock_demo.py`) was retained completely unmodified as our baseline failure witness. The corrected architecture was implemented in `src/deadlock_prevented.py`, enforcing the global order $\text{Lock A} < \text{Lock B}$ across all threads, followed by reverse-order LIFO release.

The implementation was validated using an automated 7-part unit and stress test suite (`tests/test_deadlock_prevention.py`), executing across 100 consecutive iterations. The test suite achieved a **100% pass rate (7/7 passed, 0 failed in 0.046 seconds)** with zero deadlocks. A comparison confirms that the corrected implementation completes cleanly in **0.00675 seconds (~6.75 ms)**, whereas the deadlocked baseline hangs permanently until being aborted by the parent watchdog process at **3.1648 seconds**. Note that the 100 stress-test runs serve as empirical evidence of runtime stability under contention; the universal guarantee of deadlock-freedom is established mathematically by Havender's acyclic resource ordering theorem.

---

## 2. Implementation Explanation (`src/deadlock_prevented.py`)

The remediated program is structured around the `run_prevented_deadlock()` function and worker threads:

```python
# Core logic extracted from src/deadlock_prevented.py
def run_prevented_deadlock(...):
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    start_barrier = threading.Barrier(2)

    def thread_1_worker():
        start_barrier.wait(timeout=timeout) # Synchronize concurrent start
        with lock_a:                        # Step 1: Acquire Lock A first
            with lock_b:                    # Step 2: Acquire Lock B second
                # Critical Section Execution
                pass
            # Lock B released first (LIFO)
        # Lock A released second (LIFO)

    def thread_2_worker():
        start_barrier.wait(timeout=timeout) # Synchronize concurrent start
        with lock_a:                        # Step 1: RE-ORDERED: Acquire Lock A first!
            with lock_b:                    # Step 2: RE-ORDERED: Acquire Lock B second!
                # Critical Section Execution
                pass
            # Lock B released first (LIFO)
        # Lock A released second (LIFO)
```

### Key Architectural Mechanisms

1. **Global Acquisition Order ($\text{Lock A} \to \text{Lock B}$):**
   - Both Thread 1 and Thread 2 strictly acquire `lock_a` before attempting to acquire `lock_b`.
   - Thread 2's acquisition sequence was re-engineered from $\langle B, A \rangle$ to $\langle A, B \rangle$, aligning with Thread 1.
2. **Reverse Order Release ($\text{Lock B} \to \text{Lock A}$):**
   - Python's nested `with lock_a: with lock_b:` context managers inherently enforce Last-In, First-Out (LIFO) lock release semantics.
   - Upon completing the critical section, `lock_b.__exit__()` executes first, followed by `lock_a.__exit__()`.
3. **Pre-Acquisition Concurrent Start:**
   - A `threading.Barrier(2)` is positioned *before* either thread requests Lock A. This ensures both threads launch and contend for Lock A simultaneously.
   - **Crucial Design Rule:** No barrier is placed *between* the acquisition of Lock A and Lock B. Placing a barrier between locks would force Thread 1 to hold Lock A while waiting for Thread 2 to acquire Lock A, which is impossible because Lock A is mutually exclusive.
4. **Bounded Thread Joins:**
   - Both worker threads are joined using explicit timeouts: `t1.join(timeout=timeout)` and `t2.join(timeout=timeout)`.
   - The function checks `t.is_alive()` and reports structured completion dictionaries, preventing test harnesses from hanging.

---

## 3. Important Engineering Decisions

| Code Decision | Technical Rationale |
| :--- | :--- |
| **Preservation of `deadlock_demo.py`** | The baseline file is preserved without a single character modified so that reviewers can independently verify the before-and-after failure transition. |
| **Separation of Concerns via `run_prevented_deadlock()`** | Encapsulating the run in a parameterized function enables automated unit testing, stress loops, trace logging, and shared memory assertions without subprocessing overhead. |
| **Placement of `Barrier(2)` Before Lock A** | In the baseline code, the barrier was placed *between* Lock A and Lock B, forcing asymmetric possession. In the corrected code, the barrier is placed *before* any lock is requested, guaranteeing genuine concurrent race conditions on Lock A without deadlock. |
| **Context Manager (`with`) Idiom** | Utilizing Python context managers guarantees exception safety: even if an unexpected exception occurs in the inner critical section, both Lock B and Lock A are deterministically released by the Python runtime unwind mechanism. |
| **Parametric Shared Counter** | An optional shared list `shared_counter = [0]` was added to verify mutual exclusion and data race-freedom under high iteration counts ($N$ increments by $T_1$ and $N$ by $T_2$ must equal exactly $2N$). |

---

## 4. Test Methodology (`tests/test_deadlock_prevention.py`)

The test suite evaluates 7 specific operational and invariant properties:

1. **`test_both_threads_complete_successfully`:**
   - Verifies that both threads finish and that `both_completed == True` with `error is None`.
2. **`test_no_thread_remains_blocked_after_timeout`:**
   - Asserts that both threads terminate within a fraction of a second, well before the 2.0-second safety timeout boundary.
3. **`test_both_threads_follow_same_acquisition_order`:**
   - Inspects an internal chronological execution trace to verify that for both $T_1$ and $T_2$, the event `Acquired_A` precedes `Acquired_B`.
4. **`test_repeated_concurrent_execution_100_iterations`:**
   - Executes 100 consecutive full concurrent thread runs in a tight loop.
   - Verifies a **100% completion rate** (0 deadlocks across 100 iterations) and computes the average execution latency.
5. **`test_shared_critical_section_integrity`:**
   - Runs 50 critical section iterations per thread concurrently with a shared counter.
   - Verifies that the final count is exactly 100, proving mutual exclusion and the absence of race conditions.
6. **`test_correct_lock_release_on_exception`:**
   - Injects a `ValueError` inside the nested critical section of a worker thread.
   - Verifies that both Lock A and Lock B are safely released and immediately acquirable by other threads without deadlocking.
7. **`test_reverse_order_release_lifo`:**
   - Validates via execution trace that `Releasing_B` occurs strictly before `Releasing_A`.

---

## 5. Actual Test Results & Verification Output

### Test Execution Command
```powershell
python -m unittest tests/test_deadlock_prevention.py -v
```

### Verbatim Automated Test Run Output
```text
test_both_threads_complete_successfully (tests.test_deadlock_prevention.TestDeadlockPrevention.test_both_threads_complete_successfully)
Test that both Thread 1 and Thread 2 complete normally without blocking. ... ok
test_both_threads_follow_same_acquisition_order (tests.test_deadlock_prevention.TestDeadlockPrevention.test_both_threads_follow_same_acquisition_order)
Verify that both Thread 1 and Thread 2 follow the exact same global order: ... ok
test_correct_lock_release_on_exception (tests.test_deadlock_prevention.TestDeadlockPrevention.test_correct_lock_release_on_exception)
Verify that if an unhandled exception occurs inside the critical section, ... ok
test_no_thread_remains_blocked_after_timeout (tests.test_deadlock_prevention.TestDeadlockPrevention.test_no_thread_remains_blocked_after_timeout)
Test that neither thread is alive or hanging after execution completes. ... ok
test_repeated_concurrent_execution_100_iterations (tests.test_deadlock_prevention.TestDeadlockPrevention.test_repeated_concurrent_execution_100_iterations)
Stress test: Execute 100 consecutive concurrent runs. ... ok
test_reverse_order_release_lifo (tests.test_deadlock_prevention.TestDeadlockPrevention.test_reverse_order_release_lifo)
Verify that locks are released in exact reverse order of acquisition: ... ok
test_shared_critical_section_integrity (tests.test_deadlock_prevention.TestDeadlockPrevention.test_shared_critical_section_integrity)
Verify that shared data is correctly protected and race-free. ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.046s

OK

[STRESS TEST] 100 iterations completed: 100% success. Avg duration: 0.379 ms
```

### Metrics Summary
- **Total Tests Executed:** 7
- **Passed:** 7 (100%)
- **Failed / Errored:** 0 (0%)
- **Stress Test Iteration Count:** 100 consecutive multi-threaded runs.
- **Stress Test Success Rate:** 100 / 100 (0 deadlocks observed).
- **Average Execution Duration per Run:** **0.379 milliseconds**.

---

## 6. Baseline vs. Corrected Empirical Comparison

Both programs were executed and benchmarked independently under identical hardware and OS conditions:

| Evaluation Metric | Baseline Implementation (`deadlock_demo.py`) | Corrected Implementation (`deadlock_prevented.py`) | Performance Delta / Impact |
| :--- | :--- | :--- | :--- |
| **Lock Acquisition Order** | $T_1: \langle A, B \rangle$ vs $T_2: \langle B, A \rangle$ (Asymmetric) | $T_1: \langle A, B \rangle$ and $T_2: \langle A, B \rangle$ (Strict Hierarchical) | Eliminates Circular Wait |
| **Deadlock Occurrence** | **100% Deadlock Rate** (Every run hangs) | **0% Deadlock Rate** (0 deadlocks across 100 runs) | **Complete Liveness Restoration** |
| **Thread Completion Status** | Failed (Both threads blocked permanently) | **Success** (Both threads finished cleanly) | Normal program termination |
| **Execution Duration** | **3.1648 seconds** (Dominated by 3.0s watchdog timeout) | **0.006751 seconds** (Direct unblocked execution) | **Different Timing Boundary** (Baseline reflects 3.0s watchdog timeout to abort deadlock; corrected reflects unhindered completion in milliseconds) |
| **Termination Mechanism** | Unclean: Forcibly killed via `process.terminate()` | Clean: Normal exit of thread functions and joins | No process kills or orphaned handles |
| **Shared Critical Data Integrity** | Compromised / Incomplete | **Verified**: Shared counter exactly equals $2N$ | Mutual exclusion fully preserved |
| **OS Thread State at Exit** | `WAITING` / `BLOCKED` in mutex wait-queues | `TERMINATED` / `JOINED` | Zero orphaned threads |

---

## 7. Limitations & Real-World Concurrency Constraints

While Hierarchical Resource Ordering completely solves the two-lock deadlock in Challenge D1, sound operating systems engineering requires acknowledging its fundamental boundaries and limitations:

### A. No Guarantee of Fairness or Absence of Starvation
> **IMPORTANT NOTE:** **Hierarchical Resource Ordering does NOT guarantee fairness, nor does it make thread starvation impossible.**
- **Underlying Mutex Mechanics:** In Python (and underlying operating systems such as Windows and Linux), standard mutexes (`threading.Lock()`, Windows CriticalSection / SRWLock, Linux futex) do not guarantee strict First-In, First-Out (FIFO) queue servicing.
- **Scheduler Re-Acquisition Hazard:** When Thread 1 releases Lock A, the OS scheduler may immediately grant Lock A back to Thread 1 if Thread 1 re-enters the loop quickly, starving Thread 2.
- **Asymmetric Priorities:** If Thread 1 is scheduled with higher priority or runs on a dedicated high-frequency core, Thread 2 may experience prolonged wait times.

### B. Developer Discipline & Global Knowledge Requirement
- **Static Coupling:** Hierarchical ordering relies entirely on developer discipline. If any developer, library routine, or third-party module introduces a function that acquires Lock B before Lock A, the circular wait condition is instantly reintroduced.
- **Dynamic Lock Addressing:** In systems where locks represent dynamic entities (e.g., locking bank account $X$ and bank account $Y$ during a transfer), the lock order cannot be hardcoded by variable name. It requires dynamic runtime sorting based on unique memory addresses or integer IDs:
  $$\text{if } \text{id}(L_1) < \text{id}(L_2): \ \text{lock}(L_1); \ \text{lock}(L_2) \quad \text{else}: \ \text{lock}(L_2); \ \text{lock}(L_1)$$

### C. Reduced Concurrency in Complex Systems
- If thread $T_2$ only needs to read resource B and does not need resource A, forcing $T_2$ to acquire Lock A first would unnecessarily serialize execution with thread $T_1$, reducing parallelism.

---

## 8. Conclusion

Phase 4 has successfully implemented and verified **Hierarchical Resource Ordering** for CA-3 Challenge D1. The defect has been definitively eliminated, the test suite passes with 100% consistency, and the original defective baseline remains intact as academic proof of reproduction.
