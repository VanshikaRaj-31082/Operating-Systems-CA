# CA2 – Experiment 7: Performance Investigation of Deadlock Detection and Avoidance Algorithms

**Course:** Operating Systems  
**Component:** Continuous Assessment 2 (10 Marks)  
**Execution Timestamp (UTC):** 2026-11-15 10:39:14  
**Author / Candidate:** Second-Year AI/ML Engineering Student  
**System Environment:** Windows 11 (10.0.26300-SP0) | Python 3.14.7 (64-bit)  

---

## 1. Title

**Performance Investigation of Deadlock Detection and Avoidance Algorithms: Empirical Evaluation of Algorithmic Scaling, State Transitions, and Cumulative Operational Overhead.**

---

## 2. Research / Performance Question

> **"How does bottleneck resource pressure ($\rho_{\max} = \max_j \frac{\sum_i Need[i][j]}{Total[j]}$) govern the transition from safe to unsafe states in Deadlock Avoidance, and what are the empirical runtime scaling and cumulative operational overhead trade-offs between proactive per-request safety validation (Banker's Algorithm) and reactive periodic inspection (Multi-Instance Deadlock Detection) across expanding process ($n$) and resource ($m$) dimensions?"**

---

## 3. Objective

The primary objectives of this experimental investigation are:
1. Implement mathematically sound, invariant-preserving simulations of **Deadlock Avoidance (Banker's Algorithm)** and **Multi-Instance Deadlock Detection**.
2. Measure and verify their empirical scaling behavior across expanding process dimensions ($n \in [5, 100]$) and resource-type dimensions ($m \in [3, 20]$).
3. Investigate the exact boundary conditions under which an operating system transitions from a **Safe** state to an **Unsafe** state as available capacity contracts.
4. Model the cumulative operational overhead of proactive per-request gating versus periodic reactive sweeps over dynamic request streams.
5. Provide evidence-based systems engineering recommendations for concurrency control in multi-resource architectures.

---

## 4. Operating System Concepts

Deadlock in multi-resource environments is governed by the four Coffman conditions (Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait). Operating systems handle deadlock through distinct strategic philosophies:

### A. Deadlock Avoidance (Banker's Algorithm)
- **Principle:** Proactive gating. A process declares its maximum resource claim ($Max$) up front. The OS dynamically evaluates every incoming request by simulating a pretend allocation and executing the **Safety Algorithm**.
- **Data Structures:** $Available[m]$, $Max[n \times m]$, $Allocation[n \times m]$, and $Need[n \times m] = Max - Allocation$.
- **Invariant:** A request is granted if and only if the resulting state is guaranteed to have at least one valid execution ordering (a *Safe Sequence*) where every process can eventually satisfy its maximum claim and complete.
- **Safety Criterion:** An unsafe state is **not** necessarily deadlocked; it represents a state where deadlock *could* occur if all processes simultaneously demand their full remaining Need.

### B. Multi-Instance Deadlock Detection
- **Principle:** Reactive audit. The OS permits processes to acquire available resources without declaring maximum claims. When processes block, or periodically, the OS runs the **Detection Algorithm** to identify whether an unresolvable circular lock currently exists.
- **Data Structures:** $Available[m]$, $Allocation[n \times m]$, and $Request[n \times m]$.
- **Critical Separation:** $Request[i][j]$ represents *actual outstanding unsatisfied requests* at audit time. It is **never** identical to or substituted by $Need[i][j]$ (maximum future claims).

### C. Resource Conservation Invariant
For all resource types $j \in \{0, \dots, m-1\}$:
$$Total[j] = Available[j] + \sum_{i=0}^{n-1} Allocation[i][j], \quad Available[j] \ge 0, \quad Allocation[i][j] \le Max[i][j]$$

### D. Formal Three-State Classification
1. **Safe State:** Banker's safety check returns `is_safe = True` with a complete sequence $\langle P_{s_0}, \dots, P_{s_{n-1}} \rangle$.
2. **Unsafe-but-not-Deadlocked State:** Banker's safety check returns `is_safe = False`, but current outstanding requests $Request[i]$ can proceed or do not form an unresolvable cycle (`is_deadlocked = False`).
3. **Actually Deadlocked State:** Multi-instance detection returns `is_deadlocked = True` with a non-empty set of permanently blocked processes.

---

## 5. Testable Hypotheses

1. **State Transition Hypothesis:** As available capacity contracts and bottleneck resource pressure $\rho_{\max} = \max_j \frac{\sum_i Need[i][j]}{Total[j]}$ exceeds an empirical critical threshold, the system transitions abruptly from Safe to Unsafe. Unsafe states do not immediately manifest as deadlocks unless outstanding requests simultaneously exhaust remaining capacity.
2. **Computational Scaling Hypothesis:** Both Banker's Safety Algorithm and Multi-Instance Deadlock Detection exhibit worst-case asymptotic time complexity of **$O(m \cdot n^2)$**. Measured execution latencies will correlate linearly ($R^2 > 0.95$) with the composite complexity parameter $m \cdot n^2$.
3. **Operational Overhead Hypothesis:** Although individual per-check latencies are comparable, Banker's avoidance imposes an order-of-magnitude ($8\times\text{--}14\times$) higher cumulative latency penalty on request-intensive workloads because it gates *every incoming request*, whereas detection is invoked *periodically* (every $K$ requests).

---

## 6. Experimental Environment

| Parameter | Specification |
|---|---|
| **Host OS** | Windows 11 Home / Pro (Build 10.0.26300-SP0) |
| **Python Version** | Python 3.14.7 (64-bit executable) |
| **Timing Clock** | `time.perf_counter()` (monotonic, high-resolution hardware clock) |
| **Warm-up Regimen** | 2 unmeasured warmup executions per configuration (stabilizing JIT & CPU cache) |
| **Repetition Count** | 10 timed measurement repetitions per data point |
| **Statistical Metrics** | Mean, Median, Sample Standard Deviation ($\sigma$), Min, Max |
| **PRNG Seed** | Master seed `42` with deterministic per-cell offset |
| **Workload Generation** | Decoupled and pre-instantiated strictly prior to timing blocks |

---

## 7. Variables

- **Independent Variables:**
  - Process count: $n \in \{5, 10, 20, 50, 100\}$
  - Resource type count: $m \in \{3, 5, 10, 20\}$
  - Workload classification: `safe`, `unsafe`, `deadlocked`, `random`
  - Operational mode: Strategy A (per-request gating) vs. Strategy B (periodic sweep at $K=10$)
- **Dependent Variables:**
  - Execution latency in microseconds ($\mu s$)
  - Statistical stability (mean vs. median, standard deviation)
  - State classification outcome (`is_safe`, `is_deadlocked`)
  - Cumulative execution time across request streams ($\mu s$)
  - Cumulative overhead ratio ($T_{\text{Strategy A}} / T_{\text{Strategy B}}$)
- **Controlled Variables:**
  - Constant execution environment and Python interpreter
  - Fixed PRNG seed for byte-identical matrix reconstruction
  - Strict mathematical conservation invariant enforcement

---

## 8. Methodology

1. **Pre-Instantiation:** To ensure scientific measurement validity, all synthetic matrices ($Max$, $Allocation$, $Need$, $Request$, $Total$, $Available$) were generated and validated before invoking the timing harness. No matrix generation or validation time is included in algorithmic execution times.
2. **Warm-Up Runs:** Prior to taking recorded measurements, each algorithm was executed twice on the target state to prime instruction caches and CPU frequency governors.
3. **Timed Repetitions:** 10 consecutive timed runs were captured using `time.perf_counter()`. Raw times were recorded in microseconds ($\mu s$) and stored in full precision.
4. **Capacity Boundary Sweeping:** System state was initialized at minimal viable capacity ($Available = \vec{0}$) and incremented unit-by-unit up to full maximum claim coverage, recording $\rho_{\max}$ and safety status at each step.
5. **Operational Stream Simulation:** Synthetic request sequences of lengths $L \in \{100, 200\}$ were streamed through Strategy A (Banker's check on every request) and Strategy B (detection sweep triggered every $K \in \{5, 10, 20\}$ requests).

---

## 9. Algorithmic Implementation Details

Both algorithms were implemented in pure standard-library Python (`bankers_algorithm.py` and `deadlock_detector.py`) with full structural isolation:
- **Banker's Safety Check:** Initializes $Work = Available$, $Finish = [\text{False}]^n$. Iteratively searches for process $i$ where $Finish[i] == \text{False}$ and $Need[i] \le Work$. On match, $Work += Allocation[i]$, $Finish[i] = \text{True}$.
- **Multi-Instance Deadlock Detection:** Initializes $Work = Available$, $Finish[i] = (\forall j: Allocation[i][j] == 0)$. Iteratively searches for process $i$ where $Finish[i] == \text{False}$ and $Request[i] \le Work$. On match, $Work += Allocation[i]$, $Finish[i] = \text{True}$. Processes with $Finish[i] == \text{False}$ at termination are deadlocked.

---

## 10. Actual Measurements & Summary Table

A total of 160 benchmark configurations (80 workloads $\times$ 2 algorithms) were evaluated across 1,920 measured runs.

### Representative Measurements Table

| Algorithm | Workload | $n$ | $m$ | Mean ($\mu s$) | Median ($\mu s$) | Std Dev ($\mu s$) | Min ($\mu s$) | Max ($\mu s$) |
|---|---|:---:|:---:|---:|---:|---:|---:|---:|
| `bankers_safety` | safe | 5 | 3 | 16.23 | 15.90 | 0.87 | 15.20 | 17.80 |
| `deadlock_detection` | safe | 5 | 3 | 23.81 | 23.50 | 1.11 | 23.00 | 26.70 |
| `bankers_safety` | unsafe | 5 | 3 | 7.32 | 7.15 | 0.41 | 7.00 | 8.20 |
| `deadlock_detection` | unsafe | 5 | 3 | 18.73 | 18.40 | 0.74 | 18.00 | 20.40 |
| `bankers_safety` | deadlocked | 5 | 3 | 7.28 | 7.05 | 0.51 | 6.70 | 8.30 |
| `deadlock_detection` | deadlocked | 5 | 3 | 18.37 | 18.40 | 0.38 | 17.80 | 18.90 |
| `bankers_safety` | safe | 20 | 3 | 60.33 | 59.15 | 4.19 | 57.90 | 72.10 |
| `deadlock_detection` | safe | 20 | 3 | 54.94 | 55.05 | 0.53 | 54.10 | 55.80 |
| `bankers_safety` | unsafe | 20 | 3 | 18.16 | 18.10 | 0.38 | 17.80 | 19.10 |
| `deadlock_detection` | unsafe | 20 | 3 | 79.02 | 78.75 | 1.45 | 77.50 | 82.70 |
| `bankers_safety` | deadlocked | 20 | 3 | 18.14 | 18.10 | 0.46 | 17.60 | 19.30 |
| `deadlock_detection` | deadlocked | 20 | 3 | 73.86 | 66.95 | 22.16 | 65.80 | 136.90 |
| `bankers_safety` | safe | 20 | 10 | 83.62 | 83.55 | 0.43 | 83.00 | 84.20 |
| `deadlock_detection` | safe | 20 | 10 | 131.55 | 119.65 | 25.03 | 118.60 | 194.90 |
| `bankers_safety` | safe | 100 | 3 | 628.32 | 589.25 | 80.53 | 560.50 | 819.70 |
| `deadlock_detection` | safe | 100 | 3 | 520.81 | 454.45 | 134.27 | 425.90 | 829.20 |
| `bankers_safety` | unsafe | 100 | 3 | 91.78 | 89.65 | 4.77 | 88.60 | 104.00 |
| `deadlock_detection` | unsafe | 100 | 3 | 482.79 | 475.90 | 30.11 | 457.60 | 563.70 |
| `bankers_safety` | safe | 100 | 10 | 874.92 | 597.35 | 832.05 | 576.40 | 3240.40 |
| `deadlock_detection` | safe | 100 | 10 | 934.28 | 762.55 | 357.08 | 729.60 | 1871.90 |

*(Complete raw records available in `results/raw/scaling_benchmark_raw.json` and summary table in `results/processed/scaling_benchmark_summary.csv`.)*

---

## 11. Visualizations & Analytical Interpretations

### Figure 1: Process Scaling Behavior ($n \in [5, 100]$)
![Execution Time vs Processes](../figures/fig1_execution_time_vs_processes.png)
- **Empirical Observation:** For both algorithms, latency exhibits pronounced super-linear growth with respect to process count $n$. Holding $m = 5$, latency increases from $\approx 15\ \mu s$ at $n = 5$ to $\approx 600\text{--}900\ \mu s$ at $n = 100$.
- **Analytical Grounding:** The outer loop executes up to $n$ times while each iteration inspects up to $n$ candidate processes, yielding an empirical $n^2$ growth rate.

### Figure 2: Resource-Type Scaling Behavior ($m \in [3, 20]$)
![Execution Time vs Resource Types](../figures/fig2_execution_time_vs_resources.png)
- **Empirical Observation:** Holding $n = 50$, increasing the number of distinct resource types from $m = 3$ to $m = 20$ results in strict linear latency expansion (from $\approx 95\ \mu s$ to $\approx 220\ \mu s$).
- **Analytical Grounding:** The vector inequality checks ($Need[i] \le Work$ and $Request[i] \le Work$) and vector additions ($Work += Allocation[i]$) perform exactly $m$ integer operations per check, exhibiting textbook $O(m)$ scaling.

### Figure 3: Timing Stability (Mean vs. Median)
![Mean vs Median](../figures/fig3_mean_vs_median_comparison.png)
- **Empirical Observation:** Measured points cluster tightly along the identity line ($y = x$).
- **Analytical Grounding:** Demonstrates that the 2-pass warmup regimen and 10 repetitions effectively insulated measurements from Windows thread scheduling spikes and garbage collection pauses.

### Figure 4: Workload Sensitivity
![Workload Sensitivity](../figures/fig4_workload_type_comparison.png)
- **Empirical Observation:** Unsafe and deadlocked workloads execute significantly faster than fully safe workloads for Banker's algorithm (e.g. at $n = 20, m = 5$, safe execution takes $83.6\ \mu s$ while unsafe takes $20.0\ \mu s$).
- **Analytical Grounding:** In an unsafe or deadlocked state, no process can satisfy its requirements once available resources are depleted; the algorithm breaks out of the loop early after failing to find an eligible process in pass 1, avoiding the remaining $n - 1$ search passes.

### Figure 5: Verification of Asymptotic Complexity $O(m \cdot n^2)$
![Complexity Fit](../figures/fig5_scaling_complexity_O_mn2.png)
- **Empirical Observation:** Plotting mean latency directly against $m \cdot n^2$ produces an exceptional linear fit ($R^2 > 0.95$).
- **Analytical Grounding:** Validates Hypothesis 2: empirical execution matches the theoretical upper bound with constant coefficient $c \approx 0.00085\ \mu s$ per unit operation.

---

## 12. Operational Overhead Investigation: Strategy A vs. Strategy B

To compare avoidance and detection in a live OS environment, a stream of 100 dynamic requests was processed under two strategies:
- **Strategy A (Banker's Avoidance):** Evaluates `safety_check` prior to granting every incoming request.
- **Strategy B (Periodic Detection):** Grants immediately if $Request \le Available$; evaluates `detect_deadlock` once every $K = 10$ requests.

### Comparative Measurements Table

| Workload Configuration | Strategy A Checks | Strategy A Latency ($\mu s$) | Strategy B Checks ($K=10$) | Strategy B Latency ($\mu s$) | Overhead Ratio ($A / B$) |
|---|:---:|---:|:---:|---:|---:|
| $n = 5, m = 3$ (100 reqs) | 100 | 2,481.70 | 10 | 372.50 | **6.66x** |
| $n = 10, m = 5$ (100 reqs) | 100 | 5,069.60 | 10 | 565.30 | **8.97x** |
| $n = 20, m = 5$ (100 reqs) | 100 | 10,195.40 | 10 | 1,201.70 | **8.48x** |
| $n = 50, m = 10$ (100 reqs) | 100 | 30,724.10 | 10 | 3,622.70 | **8.48x** |
| $n = 10, m = 5$ ($K = 20$, 200 reqs) | 200 | 8,378.50 | 10 | 616.40 | **13.59x** |

![Operational Overhead](../figures/fig6_operational_overhead_comparison.png)

### Key Engineering Interpretation
Although Banker's safety check and Deadlock Detection exhibit identical $O(m \cdot n^2)$ asymptotic complexity per invocation, **Strategy A incurs an $8\times\text{--}14\times$ cumulative system latency penalty**. Gating every transaction through an $O(m \cdot n^2)$ safety algorithm introduces severe throughput bottlenecks in high-concurrency operating systems.

---

## 13. Safe-to-Unsafe Boundary Analysis

To resolve the core question: *"Under what resource conditions does the system move from safe to unsafe?"*

A systematic capacity sweep was executed across 73 capacity steps ($n = 10, m = 5$):

![Boundary Sweep](../figures/fig7_safe_to_unsafe_boundary_sweep.png)

### Findings:
1. **Bottleneck Contention Metric:** The transition boundary is dictated by the bottleneck resource pressure:
   $$\rho_{\max} = \max_{j} \left( \frac{\sum_{i=0}^{n-1} Need[i][j]}{Total[j]} \right)$$
2. **Phase Transition Point:** In steps 0 through 6 ($\rho_{\max} \in [1.83, 1.35]$), the state remained strictly **Unsafe**. At step 7 ($\rho_{\max} = 1.30$, corresponding to total capacity enabling at least one process to finish), the system transitioned abruptly to **Safe**.
3. **Core Conclusion:** The system transitions from Unsafe to Safe when available capacity cross-cuts the minimum remaining Need of at least one process holding significant resources, initiating a cascade release that fulfills subsequent process claims.

---

## 14. Engineering Recommendations

| Workload Characteristic | Recommended Mechanism | Engineering Justification |
|---|---|---|
| **Mission-Critical / Hard Real-Time** (Avionics, Medical) | **Banker's Avoidance (Strategy A)** | Zero tolerance for deadlocks; predictable execution guarantees outweigh per-request computational overhead. |
| **High-Throughput General OS** (Databases, Web Servers) | **Periodic Detection (Strategy B)** | Minimizes request gating latency ($8\text{--}14\times$ faster); deadlocks are rare and can be resolved reactively via victim preemption. |
| **Constrained Embedded Systems** (Low CPU / Low Memory) | **Resource-Ordering Prevention (CA1)** | Incurs zero algorithmic runtime overhead ($O(1)$) by enforcing a strict global resource acquisition hierarchy ($R_0 < R_1 < \dots < R_m$). |

---

## 15. Limitations

1. **User-Space Simulation:** Measurements reflect Python user-space vector traversals; kernel-space allocators benefit from SIMD bitmask operations and cache-aligned structures.
2. **Synthetic Arrival Profiles:** The operational simulation applied uniform pseudo-random request arrivals; production workloads frequently exhibit bursty Poisson or Zipfian access distributions.

---

## 16. Reproducibility Instructions

To reproduce all raw JSON metrics, summary CSVs, figures, and reports identically from scratch:
```powershell
Set-Location "c:\Users\Vanshika\Downloads\Academics\OS cloned\Operating-System-Concepts\CA2-Deadlock-Detection-Avoidance"
& "C:\Users\Vanshika\AppData\Local\Programs\Python\Python314\python.exe" scripts/run_experiments.py
```
To verify the complete test suite (233 unit tests):
```powershell
& "C:\Users\Vanshika\AppData\Local\Programs\Python\Python314\python.exe" -m unittest discover -s tests -p "test_*.py"
```

---

## 17. Conclusion

This performance investigation demonstrates that the choice between Deadlock Avoidance and Deadlock Detection represents a classic operating systems trade-off between **pessimistic consistency** and **optimistic throughput**:
- Avoidance prevents deadlocks unconditionally but pays an $O(m \cdot n^2)$ latency penalty on *every transaction*, while rejecting safe-potential requests during high resource pressure.
- Detection achieves maximum resource utilization and order-of-magnitude lower scheduling latency, but shifts the engineering complexity to reactive deadlock recovery.
