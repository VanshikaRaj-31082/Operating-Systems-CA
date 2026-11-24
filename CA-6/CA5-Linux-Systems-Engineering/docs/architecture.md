# CA5 Architecture & Systems Design Specification
## Linux Concurrency Failure & Lock Contention Investigation

**Project:** `CA5-Linux-Systems-Engineering`  
**Author:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University)  
**Academic Year:** 2026–2027  

---

### 1. High-Level Architecture Overview

The CA5 system is structured into four distinct layers:
1. **Operating System & Kernel Interface Layer (`/proc`, `futex`, `sched_yield`):** Interacts directly with the Linux 6.6 kernel data structures and system calls.
2. **Workload & Synchronization Engines (`src/workloads/`):** Contains controlled, parameterizable implementations of race conditions, lock contention, and deadlock scenarios.
3. **Instrumentation & Extraction Layer (`src/proc_explorer.py`, `src/environment.py`):** High-precision inspection engine extracting context switches, thread states, wait channels, and system resource metrics.
4. **Analysis, Visualization & Reporting Layer (`src/investigation_runner.py`, `src/analysis/`):** Orchestrator computing rigorous statistical aggregations, outputting CSVs/JSONs, and rendering publication figures.

```
+-----------------------------------------------------------------------------------+
|                        CA5 Systems Architecture                                   |
+-----------------------------------------------------------------------------------+
|  [Presentation & Reporting]                                                       |
|  docs/final_report.tex  |  results/figures/  |  docs/viva_questions.md            |
+-----------------------------------------------------------------------------------+
|  [Analysis & Orchestration Engine]                                                |
|  src/investigation_runner.py  <--->  src/analysis/generate_visualizations.py      |
|  config/experiment_config.json                                                    |
+-----------------------------------------------------------------------------------+
|  [Modular Workload Generators]                                                    |
|  - Race Condition (L10)   : src/workloads/race_condition.py                       |
|  - Lock Contention (L16)  : src/workloads/lock_contention.py                      |
|  - Deadlock Scenario (L17): src/workloads/deadlock_scenario.py                    |
+-----------------------------------------------------------------------------------+
|  [Linux Instrumentation & Virtual FS Layer]                                       |
|  src/environment.py  |  src/proc_explorer.py (ContextSwitchTracker, ThreadStates)  |
+-----------------------------------------------------------------------------------+
|  [Linux Kernel & Hardware Interfaces (WSL2 / Bare-Metal)]                         |
|  /proc/<pid>/status   |   /proc/<pid>/stat   |   /proc/<pid>/task/<tid>/wchan     |
|  futex system calls   |   sched_yield        |   16 Logical Cores (Intel i5-13450HX)|
+-----------------------------------------------------------------------------------+
|  [Rust Systems Extension (L41 / CA6 Bridge)]                                      |
|  rust_bridge/src/main.rs (Atomic fetch_add vs Mutex vs SpinLock)                 |
+-----------------------------------------------------------------------------------+
```

---

### 2. Component Design & Responsibilities

#### 2.1 Environmental Discovery (`src/environment.py`)
- Reads `/etc/os-release` to identify Linux distribution name, version ID, and codename.
- Queries `platform.uname()` and `/proc/version` for kernel version and compiler build flags.
- Parses `lscpu` or `/proc/cpuinfo` to detect processor model, architecture, CPU count, and NUMA nodes.
- Inspects `/proc/meminfo` to capture total, free, and available system RAM, and swap usage.
- Measures run-queue pressure via `/proc/loadavg` (1-min, 5-min, 15-min load averages).
- Verifies toolchain presence (`ps`, `top`, `lscpu`, `vmstat`, `taskset`, `nice`, `kill`, `free`, `python3`).

#### 2.2 Linux `/proc` Process Explorer (`src/proc_explorer.py`)
- **Status Parsing (`/proc/<pid>/status`):** Safely extracts `voluntary_ctxt_switches` and `nonvoluntary_ctxt_switches`, `Threads`, `VmSize`, and `VmRSS`.
- **Stat Parsing (`/proc/<pid>/stat`):** Parses user-space CPU ticks (`utime`), kernel CPU ticks (`stime`), scheduling priority (`priority`), and nice level (`nice`). Handles whitespace in process command strings.
- **Task & Wait Channel Inspection (`/proc/<pid>/task/<tid>/wchan`):** Enumerates all active thread IDs and reads their kernel wait channel (e.g. `futex_wait_queue`).
- **Context Switch Delta Tracker:** Implements a context manager that snapshots initial context switches, executes the workload, and calculates the exact delta attributable to the workload.

#### 2.3 Race Condition Engine (`src/workloads/race_condition.py`)
- **Shared State Model:** Bank balance object with integer state.
- **Unsynchronized Method:** Reads shared state, invokes POSIX `sched_yield` via `time.sleep(0)` to trigger Linux thread preemption, and writes updated value. Reliably exposes lost update anomalies.
- **Synchronized Method:** Wraps the read-yield-write sequence inside a POSIX/Python mutex (`threading.Lock`), ensuring critical section atomicity and mutual exclusion.

#### 2.4 Lock Contention Engine (`src/workloads/lock_contention.py`)
- **Coarse Global Mutex:** Single mutex shared across all $T$ threads. Every single increment requires lock acquisition and release.
- **Chunked Mutex (Batching Intervention):** Threads accumulate updates locally and update the global counter in batches of size $B=10$. Reduces lock acquisition frequency by a factor of 10.
- **Partitioned Striped Locks (Partitioning Intervention):** Threads are mapped to independent lock stripes ($S_i = \text{tid} \pmod{16}$), eliminating cross-thread serialization completely.

#### 2.5 Deadlock & Recovery Engine (`src/workloads/deadlock_scenario.py`)
- **Unmitigated Circular Deadlock:** Thread 1 acquires $L_1$ and requests $L_2$; Thread 2 acquires $L_2$ and requests $L_1$.
- **Watchdog Protection:** Background daemon thread monitors workers with a configurable timeout ($t_{\text{watchdog}} = 3.0\text{s}$). If both threads remain blocked in state `S`, the watchdog marks the trial as deadlocked and terminates safely without hanging the process.
- **Lock Hierarchy Avoidance:** Enforces global acquisition order ($L_1 \prec L_2$), breaking Coffman Condition 4.
- **Trylock Exponential Backoff Recovery:** Worker threads attempt non-blocking acquisition of the secondary lock (`acquire(timeout=...)`). Upon timeout, the worker releases the primary lock (breaking Coffman Condition 2: Hold-and-Wait), sleeps for a randomized exponential backoff delay ($t_{\text{backoff}} \sim \text{Uniform}(1\text{ms}, 2^k\text{ms})$), and retries.

---

### 3. Data Flow & Artifact Pipeline

```
[ experiment_config.json ]
            |
            v
[ src/investigation_runner.py ]
   |---> Step 1: Environment Discovery --> [ System Metadata ]
   |---> Step 2: Race Trials (L10) ------> [ Raw Observations ]
   |---> Step 3: Contention Trials (L16)-> [ Raw Observations + /proc CS ]
   |---> Step 4: Deadlock Trials (L17) --> [ Raw Observations + Watchdog ]
            |
            +---> writes [ results/raw/concurrency_investigation_raw.json ]
            |
            +---> computes summary statistics (mean, stddev, median, min, max)
            |
            +---> writes [ results/processed/*.csv ]
            |        - race_condition_summary.csv
            |        - lock_contention_summary.csv
            |        - deadlock_investigation_summary.csv
            |
            +---> writes [ results/logs/execution_log.json ]
            |
            v
[ src/analysis/generate_visualizations.py ]
            |
            +---> renders [ results/figures/ ]
                     - fig1_race_condition_accuracy.png
                     - fig2_lock_contention_throughput.png
                     - fig3_context_switches_vs_threads.png
                     - fig4_deadlock_recovery_latency.png
```

---

### 4. Safety Architecture & Laboratory Compliance

In compliance with Section 24 of the official CA5 specification:
1. **No Fork Bombs:** The framework uses bounded, pre-configured thread pools ($T \le 16$). No uncontrolled processes are spawned.
2. **Memory Boundedness:** Workloads operate strictly on small primitive counters and bounded buffers ($< 50 \text{ MB}$ total process RSS).
3. **Non-Hanging Deadlock Guarantee:** Every deadlock demonstration uses daemonic threads and an independent watchdog timer ($3.0\text{s}$) to prevent indefinite process blocking.
4. **Process Isolation:** The framework accesses only `/proc/<pid>` and `/proc/<pid>/task/<tid>` of its own process (`os.getpid()`). No unrelated system processes or root-owned files are accessed or modified.
5. **No Kernel / Cgroup Modifications:** The investigation is conducted completely within standard user-space permissions.
