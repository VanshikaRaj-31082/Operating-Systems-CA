# CA5 Experimental Methodology & Empirical Framework
## Linux Concurrency Failure & Lock Contention Investigation

**Project:** `CA5-Linux-Systems-Engineering`  
**Author:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University)  
**Academic Year:** 2026–2027  

---

### 1. The 9-Step Engineering Framework

In strict alignment with Section 4 of the official CA5 specification, this project follows the nine-step systems engineering methodology:

```
Observe -> Formulate -> Instrument -> Experiment -> Control -> Analyze -> Engineer -> Validate -> Defend
```

| Step | Formal Activity | CA5 Concrete Implementation |
| :--- | :--- | :--- |
| **1. Observe** | Inspect actual Linux system behavior. | Gathered OS, kernel, CPU, memory, and `/proc` status using `scripts/inspect_system.sh` and `src/environment.py`. |
| **2. Formulate** | Define the concurrency failure modes. | Formulated Hypotheses H1 (data race loss), H2 (contention throughput collapse & CS surge), and H3 (deadlock avoidance/recovery). |
| **3. Instrument** | Select tools and measurement points. | Developed `src/proc_explorer.py` to parse `/proc/<pid>/status`, `/proc/<pid>/stat`, and thread wait channels. Used `time.perf_counter()` for nanosecond timing. |
| **4. Experiment** | Execute controlled test suites. | Executed full experiment matrix: Race condition ($T \in [2, 4, 8, 16]$), Contention ($T \in [1, 2, 4, 8, 16]$, 3 strategies), Deadlock (3 scenarios). |
| **5. Control** | Ensure reproducibility and isolation. | Fixed operation counts, thread affinities, random seeds ($[101, 202, 303, 404, 505]$), and watchdog timeouts ($3.0\text{s}$). |
| **6. Analyze** | Statistically summarize observations. | Computed mean, median, min, max, sample standard deviation ($N > 1$), throughput, and error percentages. |
| **7. Engineer** | Implement targeted systems interventions. | Built Mutex synchronization, Chunked batching, Partitioned striped locks, Canonical lock hierarchy, and Trylock with exponential backoff. |
| **8. Validate** | Verify that interventions solve failures. | Demonstrated 0.0000% race error, 8.0x contention throughput improvement, and 0.0% deadlock rate with sub-2ms recovery. |
| **9. Defend** | Justify findings and trade-offs. | Prepared 25 comprehensive viva defence questions (`docs/viva_questions.md`) and university-level LaTeX research report (`docs/final_report.tex`). |

---

### 2. Experimental Design & Variable Matrix

#### Experiment 1: Race Condition & Correction (L10)
- **Independent Variables:**
  - Concurrency level: Thread count $T \in \{2, 4, 8, 16\}$.
  - Synchronization Mode: `unsynchronized` vs. `mutex_synchronized`.
- **Controlled Variables:**
  - Operations per thread: $O = 10,000$ increments.
  - Preemption trigger: POSIX `sched_yield` via `time.sleep(0)`.
  - Repetitions: $R = 5$ independent trials per configuration.
- **Dependent Variables:**
  - Discrepancy: $\Delta = O_{\text{expected}} - O_{\text{observed}}$.
  - Relative Error (%): $E = \frac{\Delta}{O_{\text{expected}}} \times 100\%$.
  - Execution Duration (seconds) and Throughput (ops/sec).

#### Experiment 2: Lock Contention & Context Switch Surge (L16)
- **Independent Variables:**
  - Concurrency level: Thread count $T \in \{1, 2, 4, 8, 16\}$.
  - Locking Strategy:
    1. `coarse_mutex` (Single global lock, batch size 1).
    2. `chunked_mutex` (Batching intervention, chunk size $B = 10$).
    3. `partitioned_striped` (Fine-grained striped locks, 16 independent locks).
- **Controlled Variables:**
  - Total operations: $500,000$ operations distributed evenly across threads.
  - Repetitions: $R = 5$ independent trials per configuration.
- **Dependent Variables:**
  - Throughput: $\Theta = \frac{\text{Total Operations}}{\text{Duration}}$ (ops/second).
  - Voluntary Context Switches ($\Delta_{\text{vol}}$): Sampled via `/proc/<pid>/status`.
  - Non-Voluntary Context Switches ($\Delta_{\text{nonvol}}$): Sampled via `/proc/<pid>/status`.
  - Wall-clock execution time (seconds).

#### Experiment 3: Deadlock Demonstration, Avoidance & Recovery (L17)
- **Independent Variables:**
  - Deadlock Scenario:
    1. `circular_deadlock_unmitigated` (Circular wait without mitigation).
    2. `lock_hierarchy_avoidance` (Canonical acquisition order $L_1 \prec L_2$).
    3. `trylock_exponential_backoff_recovery` (Dynamic trylock with exponential backoff).
- **Controlled Variables:**
  - Watchdog timeout: $t_{\text{watchdog}} = 3.0\text{s}$.
  - Target operations: 200 operations.
  - Repetitions: $R = 5$ independent trials per scenario.
- **Dependent Variables:**
  - Deadlock Occurrence Rate (%): Percentage of trials triggering watchdog.
  - Mean Execution / Resolution Time (seconds).
  - Operations Completed.
  - Retries count (under exponential backoff).

---

### 3. Statistical Treatment & Rigor

1. **Repetitions & Central Tendency:**
   Every experimental configuration is executed across 5 independent trials. For any metric $X = \{x_1, x_2, \dots, x_N\}$, the sample mean $\bar{x}$ is computed as:
   $$\bar{x} = \frac{1}{N} \sum_{i=1}^N x_i$$
   The median $\tilde{x}$ is reported to provide an outlier-resistant measure of central tendency.

2. **Sample Dispersion (Standard Deviation):**
   Sample standard deviation $s$ is computed with Bessel's correction ($N - 1$ degrees of freedom):
   $$s = \sqrt{\frac{1}{N - 1} \sum_{i=1}^N (x_i - \bar{x})^2}$$
   In compliance with Phase 5.1/5.2 integrity rules, when $N = 1$, standard deviation is strictly set to `None` (empty string in CSV / `null` in JSON) rather than zero.

3. **Relative Error Formulation:**
   Relative error $E$ in race condition measurements is calculated as:
   $$E = \frac{T \cdot O_{\text{thread}} - B_{\text{observed}}}{T \cdot O_{\text{thread}}} \times 100\%$$
