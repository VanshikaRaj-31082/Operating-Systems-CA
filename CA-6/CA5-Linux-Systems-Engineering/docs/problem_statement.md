# CA5 Problem Statement & Engineering Specification
## Linux Systems Engineering Challenge: Concurrency Failure & Lock Contention Investigation

**Project:** `CA5-Linux-Systems-Engineering`  
**Author:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University), Faculty of Engineering and Technology  
**Academic Year:** 2026–2027  
**Official Challenge:** **L38 — Linux Concurrency Failure & Lock Contention Investigation**  
**Integrated Sub-Challenges:**
- **L10 — Race Condition and Correction**
- **L16 — Lock Contention Investigation**
- **L17 — Deadlock Demonstration, Safe Detection, and Recovery**
- **L25 — Build a `/proc` Process Explorer & Thread Inspector**
- **L41 / CA6 Bridge — Rust Synchronization & Kernel Task Primitives**

---

### 1. Problem
Modern multi-core Linux systems rely heavily on multi-threaded execution to achieve high computational throughput. However, unmanaged concurrency introduces critical operating system failures:
1. **Data Inconsistency (Data Races):** Unsynchronized concurrent updates to shared memory variables cause silent data corruption through lost updates.
2. **Lock Contention & Performance Collapse:** Coarse-grained locking primitives force concurrent threads to block on kernel futexes, causing throughput collapse and an explosion in voluntary context switches (`voluntary_ctxt_switches`).
3. **Catastrophic Hangs (Deadlocks):** Uncontrolled lock acquisition orders produce circular wait dependencies, permanently blocking threads in kernel sleep state (`S` / `futex_wait_queue`).

### 2. OS Concept
- **Mutual Exclusion & Critical Sections:** POSIX/futex synchronization locks.
- **Kernel Scheduling & Preemption:** Completely Fair Scheduler (CFS), timeslice preemption, and POSIX `sched_yield`.
- **Context Switching:** Voluntary context switches (thread yields while blocking on a synchronization primitive) vs. non-voluntary context switches (preemption by the kernel when a timeslice expires).
- **Virtual Filesystem (`/proc`):** Kernel-exposed metrics via `/proc/<pid>/status`, `/proc/<pid>/stat`, `/proc/<pid>/task/<tid>/status`, and `/proc/<pid>/task/<tid>/wchan`.
- **Coffman Deadlock Conditions:** Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.

### 3. Research / Engineering Questions
1. **EQ1 (Race Condition):** How does the magnitude of lost updates scale with increasing thread concurrency under Linux, and does mutex synchronization eliminate data corruption without deadlocks?
2. **EQ2 (Lock Contention & Context Switches):** To what extent does coarse-grained mutex contention degrade multi-core throughput, and how does this correlate with kernel voluntary context switches recorded in `/proc/<pid>/status`?
3. **EQ3 (Deadlock & Recovery):** How can user-space circular deadlocks be detected using `/proc` thread inspection, and which engineering intervention (hierarchical lock ordering vs. trylock exponential backoff) provides optimal recovery latency and throughput?

### 4. Hypotheses
- **H1 (Data Corruption):** In unsynchronized shared-state updates, data loss relative error will increase monotonically with concurrent thread count ($T \in [2, 4, 8, 16]$) due to increased interleaving probability during preemptive yields. Mutex synchronization will achieve exactly 0.0% error.
- **H2 (Contention & Context Switches):** Coarse-grained global locking will suffer throughput collapse as concurrency increases beyond physical core saturation, directly accompanied by a monotonic surge in voluntary context switches. Critical section chunking and partitioned striped locking will restore linear scalability.
- **H3 (Deadlock Mitigation):** Canonical lock ordering will achieve 0.0% deadlock rate with sub-millisecond execution times. Trylock with randomized exponential backoff will dynamically resolve deadlocks without requiring static acquisition hierarchy, eliminating indefinite hangs.

### 5. Linux Environment
- **Operating System:** Ubuntu 26.04.1 LTS (Resolute Raccoon) on WSL2
- **Linux Kernel:** `6.6.87.2-microsoft-standard-WSL2` (#1 SMP PREEMPT_DYNAMIC x86_64)
- **Host CPU:** 13th Gen Intel(R) Core(TM) i5-13450HX (16 logical cores, 8 physical cores, 2 threads/core)
- **Host Memory:** 7.61 GB RAM total, 6.77 GB available, 2.00 GB swap
- **Python Runtime:** Python 3.14.4 (WSL2 Linux) / Python 3.14.7 (Host)
- **Linux Tools:** `/proc`, `lscpu`, `vmstat`, `ps`, `top`, `free`, `nice`, `taskset`, `kill`, `bash`

### 6. Tools
- **Bash Shell:** Orchestrates low-level environment discovery, tracing, and execution (`scripts/inspect_system.sh`, `scripts/trace_concurrency.sh`, `scripts/run_experiments.sh`).
- **Python 3:** Modular systems engineering framework (`src/environment.py`, `src/proc_explorer.py`, `src/workloads/`, `src/investigation_runner.py`).
- **Rust (L41 Extension):** Zero-cost systems bridge comparing hardware atomic `fetch_add`, OS `std::sync::Mutex`, and user-space `SpinLock` (`rust_bridge/src/main.rs`).
- **Matplotlib:** Publication-quality automated figure generation (`src/analysis/generate_visualizations.py`).

### 7. Methodology
Follows the official 9-step CA5 engineering framework:
1. **Observe:** Inspect baseline Linux process states and toolchain availability.
2. **Formulate:** Define the three concurrency failure modes (races, contention storms, circular deadlocks).
3. **Instrument:** Develop `/proc` status and stat parsers, context-switch delta trackers, and thread wait channel inspectors.
4. **Experiment:** Execute controlled, multi-repetition benchmark matrix across thread counts ($T \in [1, 2, 4, 8, 16]$) and locking strategies.
5. **Control:** Fix operation counts, deterministic random seeds, watchdog timeouts, and thread affinities.
6. **Analyze:** Compute summary statistics (mean, median, standard deviation, min, max, throughput, and error rates).
7. **Engineer:** Implement three targeted engineering interventions:
   - Intervention 1: POSIX Mutex synchronization.
   - Intervention 2: Critical section batching (chunked locks) and striped fine-grained locking.
   - Intervention 3: Canonical resource ordering and trylock with randomized exponential backoff.
8. **Validate:** Re-execute benchmarks under interventions and verify that data races are eliminated, throughput is scaled, and deadlocks are resolved.
9. **Defend:** Prepare viva defence answers and LaTeX research report connecting findings to CA4 and CA6.

### 8. Implementation
- `src/environment.py`: Discovers hardware topology, kernel release, and Linux utilities.
- `src/proc_explorer.py`: Parses `/proc/<pid>/status`, `/proc/<pid>/stat`, and `/proc/<pid>/task/<tid>/wchan`.
- `src/workloads/race_condition.py`: Implements unsynchronized vs. mutex synchronized shared balance updates.
- `src/workloads/lock_contention.py`: Implements coarse, chunked, and partitioned locking with context-switch instrumentation.
- `src/workloads/deadlock_scenario.py`: Implements circular deadlock, watchdog monitoring, lock ordering, and trylock backoff.
- `src/investigation_runner.py`: Master runner orchestrating experiments, calculating statistics, and serializing JSON/CSV artifacts.

### 9. Evidence
- **Raw Measurements:** `results/raw/concurrency_investigation_raw.json` (59 KB of structured trial observations).
- **Processed CSVs:** `results/processed/race_condition_summary.csv`, `lock_contention_summary.csv`, `deadlock_investigation_summary.csv`.
- **System Execution Logs:** `results/logs/execution_log.json`.
- **Visualizations:** Four high-resolution figures in `results/figures/`.

### 10. Engineering Interventions
1. **Data Race:** Transitioned from unsynchronized read-modify-write to POSIX/Python mutual exclusion (`threading.Lock`).
2. **Lock Contention:** Transformed single coarse-grained critical section into local batching (chunk size 10) and striped multi-lock partitioning.
3. **Deadlock:** Enforced strict resource acquisition hierarchy (`Lock 1` before `Lock 2`) and trylock with exponential backoff.

### 11. Validation
- **Race Correction:** Reduced relative data loss from 93.7% down to 0.0000% across all thread counts.
- **Contention Throughput:** Increased multi-threaded throughput from $5.95 \times 10^6$ ops/sec (coarse) to $47.68 \times 10^6$ ops/sec (chunked batching), representing an 8.0x throughput acceleration.
- **Deadlock Elimination:** Eliminated 100% of deadlocks, reducing latency from 3.09s (watchdog abort) to 1.08ms (trylock backoff).
- **Automated Tests:** 32 / 32 test cases passing cleanly in both Linux and Windows environments.

### 12. Conclusion
Operating system concurrency cannot be treated as a pure user-space programming detail. When synchronization is absent, thread scheduling causes massive silent data loss. When synchronization is overly coarse, kernel futex blocking and context switching collapse execution performance. By instrumenting Linux via `/proc` and applying targeted systems engineering interventions, data races are eliminated, scalability is restored, and deadlocks are avoided. This provides the empirical foundation for implementing task scheduling and synchronization in the CA6 Rust Micro-OS.
