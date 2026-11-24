# CA5 Limitations, Threats to Validity, and Environmental Trade-offs
## Linux Systems Engineering: Concurrency Failure & Lock Contention Investigation

**Project:** `CA5-Linux-Systems-Engineering`  
**Author:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University)  
**Academic Year:** 2026–2027  

---

### 1. Threats to Validity Analysis

In academic systems research, threats to experimental validity must be explicitly analyzed to establish the boundaries and reliability of the conclusions.

#### 1.1 Construct Validity
- **Construct:** Does the measurement reflect the intended operating system mechanism?
- **Analysis:**
  - *Context Switches:* We measure context switches via the Linux virtual filesystem `/proc/<pid>/status`. This directly accesses the kernel's `task_struct->nivcsw` (non-voluntary) and `task_struct->nvcsw` (voluntary) counters. When a thread blocks on a POSIX mutex futex, the Linux kernel increments `nvcsw`. Thus, voluntary context switches directly measure synchronization wait events.
  - *Data Races:* We trigger thread yields via POSIX `sched_yield` (`time.sleep(0)`) between the read and write steps. In pure Python without this yield, the GIL (Global Interpreter Lock) bytecode evaluation loop can mask data races if the timeslice interval ($5\text{ms}$) exceeds the duration of a loop iteration. By introducing `sched_yield`, we reliably expose the multi-core preemption hazard that occurs in native compiled systems code.

#### 1.2 Internal Validity
- **Construct:** Are observed differences caused by the independent variables rather than confounding factors?
- **Analysis:**
  - *Background System Noise:* The host system runs background daemons, WSL hypervisor tasks, and system services. To control for this, every configuration was executed across 5 repetitions with warm-up runs, and results were aggregated using both mean and median metrics.
  - *Timer Precision:* Timings were captured using `time.perf_counter()`, which provides access to the CPU's invariant Time Stamp Counter (TSC) with sub-microsecond resolution, avoiding low-resolution system clock jitters.
  - *Dynamic Frequency Scaling (Intel Turbo Boost):* Thermal throttling and frequency scaling across P-cores and E-cores on the Intel Core i5-13450HX can introduce timing variances. We mitigated this by evaluating relative throughput ratios and context switch counts, which are invariant to clock frequency.

#### 1.3 External Validity
- **Construct:** How well do these findings generalize to other operating systems and production environments?
- **Analysis:**
  - *WSL2 Virtualization vs. Bare-Metal Linux:* Experiments were conducted inside a Linux VM managed by WSL2 running Microsoft Linux Kernel `6.6.87.2-microsoft-standard-WSL2`. While the WSL2 kernel is a genuine Linux kernel running inside a Hyper-V lightweight utility VM, virtualization adds a minor layer of hypervisor context-switch overhead compared to bare-metal Linux. However, the fundamental synchronization mechanics (futexes, CFS scheduling, `/proc` virtual filesystem) are identical to standard upstream Linux.
  - *Workload Representativeness:* The synthetic banking balance and striped counter workloads model typical shared database and in-memory cache contention patterns. Real-world applications typically have mixed CPU-bound and I/O-bound phases.

#### 1.4 Statistical Conclusion Validity
- **Construct:** Are the statistical conclusions justified by sample size and variance?
- **Analysis:**
  - Sample sizes ($N = 5$ repetitions per cell, totaling 115 experimental runs) provide tight confidence intervals for deterministic synchronization mechanisms.
  - Standard deviations are reported alongside means to document measurement dispersion. For $N = 1$ edge cases, sample standard deviation is strictly treated as `None` to prevent false precision.

---

### 2. Technical Limitations

1. **User-Space vs. Kernel-Space Concurrency:** All experiments execute in Linux user space. Mutexes are implemented via the glibc/POSIX `futex` (fast userspace mutex) system call. While this accurately models application-level systems programming, it does not directly instrument kernel-space spinlocks or interrupt service routines (which will be implemented in CA6).
2. **Watchdog Deadlock Mitigation:** The watchdog timer in Challenge L17 operates at user-space thread level. In a production Linux kernel, deadlocks in kernel code cause kernel panics or hung task warnings (`hung_task_timeout_secs`).
3. **P-Core and E-Core Heterogeneity:** The host processor features 6 Performance Cores (12 threads) and 4 Efficient Cores (4 threads). Beyond 12 concurrent threads, workloads run partially on E-cores, introducing heterogeneous execution speeds.
