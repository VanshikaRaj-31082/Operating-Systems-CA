# CA5 Viva & Technical Defence Guide
## 25 Comprehensive Questions & Answers for Technical Examination

**Project:** `CA5-Linux-Systems-Engineering`  
**Candidate:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University), Faculty of Engineering and Technology  
**Academic Year:** 2026–2027  
**Official Challenge:** **L38 — Concurrency Failure & Lock Contention Investigation with Real Linux `/proc` Instrumentation**

---

### Category 1: Operating System & Linux Fundamentals

#### Q1: What is the primary objective of CA5, and how does it differ from CA4?
**Answer:**  
CA4 investigated deadlock detection through simulation algorithms on mathematical models (Wait-For Graphs and Banker's reduction). CA5 transitions from simulation to real systems engineering: observing, instrumenting, and controlling actual Linux kernel behavior, threads, synchronization primitives, context switches, and virtual filesystems (`/proc`) on a real multi-core Linux system.

#### Q2: What is the virtual filesystem `/proc`, and how does the Linux kernel populate it?
**Answer:**  
`/proc` is a pseudo-filesystem generated dynamically by the Linux kernel in memory (it does not exist on physical disk). It serves as an interface between user space and kernel data structures. When user space reads `/proc/<pid>/status` or `/proc/<pid>/stat`, the kernel intercepts the VFS `read()` system call, queries the process's `task_struct`, formats the fields into ASCII text, and returns them to the user buffer.

#### Q3: What is the difference between voluntary and non-voluntary context switches in Linux?
**Answer:**  
- **Voluntary Context Switches (`nvcsw`):** Occur when a thread voluntarily relinquishes the CPU before its timeslice expires because it must wait for an unavailable resource (e.g. blocking on an I/O operation, sleeping, or waiting for a contended POSIX mutex futex).
- **Non-Voluntary Context Switches (`nivcsw`):** Occur when the Linux kernel's Completely Fair Scheduler (CFS) forcibly preempts a thread because its allocated timeslice has expired or a higher-priority task has become runnable.

#### Q4: What kernel mechanism underlies POSIX mutexes on Linux?
**Answer:**  
POSIX mutexes in Linux (`pthread_mutex_t`) are implemented using **futexes** (Fast Userspace Mutexes). In the uncontended case, a thread acquires or releases the lock using an atomic compare-and-swap (CAS) instruction entirely in user space without entering the kernel. In the contended case, the thread issues a `sys_futex` system call with the `FUTEX_WAIT` command, placing the thread to sleep on a kernel wait queue, which increments `voluntary_ctxt_switches`.

#### Q5: What does `/proc/<pid>/task/<tid>/wchan` reveal during a thread hang?
**Answer:**  
`wchan` (wait channel) outputs the name of the kernel function in which a sleeping or blocked thread is currently waiting. For example, during a mutex contention or circular deadlock incident, `/proc/<pid>/task/<tid>/wchan` displays `futex_wait_queue` or `do_futex`. This provides direct empirical proof that the thread is blocked in kernel space waiting for a futex wake event.

---

### Category 2: Concurrency, Race Conditions & Lock Contention

#### Q6: How did you reproduce a data race in Python despite the Global Interpreter Lock (GIL)?
**Answer:**  
In Python, simple arithmetic operations in a tight loop can execute within a single interpreter timeslice without thread preemption. To expose the underlying multi-core race condition, we introduced POSIX `sched_yield` via `time.sleep(0)` between the read (`current = self.balance`) and the store (`self.balance = current + 1`). This forces the kernel to yield the CPU timeslice, allowing other threads to interleave and overwrite shared state, causing between 50% and 93.7% lost updates.

#### Q7: Why does data loss increase monotonically with thread count in unsynchronized execution?
**Answer:**  
As concurrent thread count increases from 2 to 16, the number of competing execution contexts attempting to read and write the shared memory variable simultaneously increases. The probability that multiple threads read the identical stale value before any single thread commits its increment increases asymptotically toward 1, resulting in 93.7% data loss at $T=16$.

#### Q8: What happened to execution time and throughput when mutex synchronization was applied to the race condition?
**Answer:**  
Mutex synchronization eliminated 100% of the lost updates (achieving 0.0000% error across all thread counts). However, execution time increased (e.g. from 6.2s to 24.5s at 16 threads) because serialization forced threads to queue sequentially, demonstrating the fundamental systems engineering trade-off between absolute consistency and execution concurrency.

#### Q9: What is lock contention, and how did you measure its performance impact in Challenge L16?
**Answer:**  
Lock contention occurs when multiple concurrent threads attempt to acquire the same mutual exclusion primitive at the same time. We measured its impact across $T \in [1, 2, 4, 8, 16]$ threads using:
1. Throughput in operations per second ($\Theta = \text{Total Ops} / \text{Duration}$).
2. Kernel voluntary context switches extracted via `/proc/<pid>/status`. Under coarse global locking, throughput stalled at $\approx 5.95 \times 10^6$ ops/sec, while voluntary context switches surged from 3.2 to 36.6.

#### Q10: Describe the two engineering interventions implemented to alleviate lock contention in L16.
**Answer:**  
1. **Intervention 1 (Chunked Batching):** Threads accumulate increments locally and acquire the global mutex only once every $B=10$ operations. This reduced lock acquisition frequency tenfold, boosting throughput by 8.0x (from 5.95 MOps/s to 47.68 MOps/s).
2. **Intervention 2 (Partitioned Striped Locking):** The single global counter was divided into 16 independent stripe counters, each guarded by its own independent lock. Threads were hashed to stripe $S_i = \text{tid} \pmod{16}$, completely eliminating cross-thread lock contention.

---

### Category 3: Deadlock Demonstration, Avoidance & Recovery

#### Q11: What are the four Coffman conditions, and how were they demonstrated in Challenge L17?
**Answer:**  
1. **Mutual Exclusion:** Each lock can be held by only one thread at a time.
2. **Hold and Wait:** Thread 1 holds Lock 1 and requests Lock 2; Thread 2 holds Lock 2 and requests Lock 1.
3. **No Preemption:** Neither thread can forcibly seize a lock held by the other.
4. **Circular Wait:** Thread 1 waits for Lock 2 held by Thread 2, while Thread 2 waits for Lock 1 held by Thread 1.  
All four conditions were demonstrated using two shared mutex locks acquired in reverse order with a staggered hold delay.

#### Q12: How did you ensure that the deadlock demonstration did not hang your system (Safety Section 24)?
**Answer:**  
We implemented an independent **Watchdog Safety Monitor**. The worker threads were spawned as daemon threads, and a dedicated watchdog monitored their completion with a 3.0-second timeout. If the threads remained deadlocked in kernel state `S` after the timeout, the watchdog detected the failure, recorded the thread states via `/proc`, marked the trial as deadlocked, and allowed the benchmark harness to proceed safely without hanging the process.

#### Q13: How does the Lock Hierarchy intervention prevent deadlocks?
**Answer:**  
Lock Hierarchy enforces a global total ordering on all lock acquisitions ($L_1 \prec L_2$). Every thread must acquire $L_1$ before attempting to acquire $L_2$. This mathematically eliminates Coffman Condition 4 (Circular Wait), ensuring that a circular dependency can never form. In our experiments, lock hierarchy reduced the deadlock rate from 100.0% to 0.0% with sub-2ms completion times.

#### Q14: How does Trylock with Exponential Backoff resolve deadlocks dynamically?
**Answer:**  
Instead of blocking indefinitely on the second lock, threads use a non-blocking or timed acquisition (`acquire(timeout=0.02)`). If the secondary lock cannot be acquired within the timeout window, the thread immediately releases its primary lock—breaking Coffman Condition 2 (Hold and Wait). The thread then sleeps for a randomized exponential backoff duration ($t \sim \text{Uniform}(1\text{ms}, 2^k\text{ms})$) before retrying, preventing livelock and allowing the other thread to complete.

---

### Category 4: Toolchain, Reproducibility & Environment

#### Q15: What host environment was used, and how was Linux accessibility verified?
**Answer:**  
The host system is Windows 11 running WSL2 with Ubuntu 26.04.1 LTS (Resolute Raccoon), powered by the Microsoft Linux Kernel `6.6.87.2-microsoft-standard-WSL2` on an Intel Core i5-13450HX processor (16 logical cores). Linux accessibility was verified through native commands (`uname -a`, `cat /etc/os-release`, `lscpu`, `vmstat`, `/proc/meminfo`).

#### Q16: Why did you use both Bash and Python in this project?
**Answer:**  
In accordance with CA5 Section 6, Bash is the native Linux orchestration language, used for low-level system inspection (`scripts/inspect_system.sh`) and experiment execution (`scripts/run_experiments.sh`). Python is the systems automation and statistical engine, used for thread management, `/proc` parsing, numerical data aggregation, and structured JSON/CSV serialization.

#### Q17: How did you handle edge cases in sample standard deviation?
**Answer:**  
In sample statistics, standard deviation requires $N > 1$ degrees of freedom ($N - 1$ in Bessel's correction). When $N = 1$, sample standard deviation is mathematically undefined. Our data processing engine explicitly sets `stddev` to `None` (empty string in CSV and `null` in JSON) rather than misrepresenting it as `0.0`.

#### Q18: What is the purpose of deterministic random seeds in your configuration?
**Answer:**  
Deterministic seeds ($[101, 202, 303, 404, 505]$) ensure experimental reproducibility. Any external researcher running the benchmark with the documented configuration will generate identical pseudo-random backoff intervals and workload schedules, ensuring that results can be independently audited and verified.

---

### Category 5: CA4 Continuity & CA6 Rust Micro-OS Bridge

#### Q19: How does CA5 connect conceptually to your findings in CA4?
**Answer:**  
CA4 investigated deadlock detection on single-instance Wait-For Graphs and multi-instance Banker's resource matrices under simulated allocation patterns. CA5 validates these theoretical concepts on a real OS: single-instance mutex locks in user space form physical Wait-For Graphs in kernel memory, where Circular Wait produces actual thread hangs observable in `/proc/<pid>/task/<tid>/wchan`.

#### Q20: What is the technical difference between user-space spinlocks and kernel mutexes demonstrated in your Rust bridge?
**Answer:**  
As demonstrated in `rust_bridge/src/main.rs`:
- **Spinlocks:** Use atomic compare-and-swap (`AtomicBool::compare_exchange`) in a busy loop. They consume 100% CPU core capacity while waiting, but introduce zero context-switch latency.
- **Mutexes:** Wrap OS futexes. If the lock is held, the calling thread is put to sleep by the kernel, yielding the CPU to other tasks and incurring voluntary context-switch overhead.

#### Q21: In the CA6 Rust Micro-OS, where will spinlocks be used versus sleeping mutexes?
**Answer:**  
In the CA6 Micro-OS kernel:
- **Spinlocks** must be used inside interrupt service routines (ISRs) and the core scheduler, because interrupt contexts cannot sleep or invoke the scheduler.
- **Sleeping Mutexes** will be used for task-level synchronization, where long-running critical sections place tasks onto a wait queue and call `schedule()`.

#### Q22: How will a process/task be represented in the CA6 Rust Micro-OS?
**Answer:**  
In CA6, a task is represented by a `TaskControlBlock` (TCB) struct containing:
1. A unique `task_id: usize`.
2. Execution state (`Ready`, `Running`, `Blocked`).
3. Saved hardware CPU registers (`rsp`, `rip`, `rflags`, `rax`, `rbx`, etc.).
4. A private stack memory allocation.
5. A pointer/index to the next task in the scheduler's run queue.

#### Q23: How will context switching be implemented in CA6 compared to what was observed in CA5?
**Answer:**  
In CA5, context switches were observed as statistical counters in `/proc/<pid>/status`. In CA6, context switching will be implemented directly in bare-metal assembly/Rust: saving the current task's callee-saved registers to its stack, updating its TCB `rsp`, switching `RSP` to the new task's stack pointer, and restoring the new task's registers before executing `ret`.

#### Q24: What is the role of atomic instructions in modern OS engineering?
**Answer:**  
Atomic instructions (e.g. `LOCK XADD`, `CMPXCHG` on x86_64) provide hardware-enforced read-modify-write atomicity across multi-core CPU caches via cache-coherency protocols (MESI). They allow implementing lock-free data structures and basic synchronization primitives without needing operating system system calls.

#### Q25: What is the most critical systems engineering insight you gained from CA5?
**Answer:**  
Concurrency is not merely an application-level programming problem—it is intimately coupled to operating system scheduling, cache coherency, and kernel synchronization mechanisms. Unmanaged concurrency causes silent data corruption; unmanaged locking causes severe throughput collapse due to context switching storms; and unmanaged acquisition ordering causes catastrophic deadlocks. High-performance systems engineering requires aligning software locking architectures with underlying OS kernel primitives.
