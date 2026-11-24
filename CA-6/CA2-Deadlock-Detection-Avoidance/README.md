# CA2 – Experiment 7: Performance Investigation of Deadlock Detection and Avoidance Algorithms

**Course:** Operating Systems  
**Component:** Continuous Assessment 2 (10 Marks)  
**Track:** Performance Investigation & Simulation  
**Author / Candidate:** Second-Year AI/ML Engineering Student  
**System Environment:** Windows 11 | Python 3.14.7 | Matplotlib 3.11.2  

---

## 1. Executive Summary

This project presents an empirical and algorithmic performance investigation comparing **Deadlock Avoidance** (Dijkstra's Banker's Algorithm) and **Multi-Instance Deadlock Detection** (Silberschatz/Galvin/Gagne model). 

The experimental suite investigates:
1. **Algorithmic Complexity Scaling:** Scaling behavior across expanding process dimensions ($n \in [5, 100]$) and resource-type dimensions ($m \in [3, 20]$).
2. **State Transition Dynamics:** Boundary conditions governing the phase transition from Safe to Unsafe states as a function of the bottleneck resource pressure ratio $\rho_{\max} = \max_j \frac{\sum_i Need[i][j]}{Total[j]}$.
3. **Cumulative Operational Overhead:** The real-world system latency of proactive per-request gating (checking safety at every allocation) versus periodic reactive auditing (running multi-instance detection every $K$ operations).

The core simulation, mathematical models, workload generators, and test suites are implemented in pure Python (standard library only). The complete test suite contains **233 unit and property tests with 100% pass rate**.

---

## 2. Research Question & Hypotheses

### Research Question
> *"How does bottleneck resource pressure ($\rho_{\max}$) govern the transition from safe to unsafe states in Deadlock Avoidance, and what are the empirical runtime scaling and cumulative operational overhead trade-offs between proactive per-request safety validation (Banker's Algorithm) and reactive periodic inspection (Multi-Instance Deadlock Detection) across expanding process ($n$) and resource ($m$) dimensions?"*

### Hypotheses & Empirical Findings
| Hypothesis | Theoretical Basis | Empirical Finding | Status |
| :--- | :--- | :--- | :--- |
| **H1: Algorithmic Scaling** | Both algorithms have worst-case theoretical complexity of $O(m \cdot n^2)$. | Execution time grows quadratically with $n$ ($R^2 > 0.95$ on linear fit vs $m \cdot n^2$) and linearly with $m$. Absolute single-execution runtimes are near-identical (~$15\ \mu\text{s}$ at $n=5$ to ~$600\text{--}900\ \mu\text{s}$ at $n=100$). | **Validated** |
| **H2: Workload Sensitivity** | Detection terminates in a single scan ($O(m \cdot n)$) when all processes have zero requests or zero allocations. | Detection on safe/zero-request states completes in ~$70\ \mu\text{s}$ vs ~$150\ \mu\text{s}$ on deadlocked states. Banker's avoidance exhibits higher variance on unsafe states due to exhausting all candidate searches before failing. | **Validated** |
| **H3: Phase Transition** | Unsafe transitions occur sharply when bottleneck resource pressure $\rho_{\max} > 1.0$ and Available headroom drops below the minimum remaining need of any process. | In a 73-step contraction sweep ($n=10, m=5$), the system transitioned abruptly from Unsafe to Safe at step 7 ($\rho_{\max} = 1.30$, Available = $[4, 3, 2, 3, 4]$), where at least one process could satisfy its remaining Need and release resources. | **Validated** |
| **H4: Operational Overhead** | Proactive per-request checking incurs prohibitive cumulative latency compared to periodic batch inspection. | Over a 100-request stream, Banker's per-request gating required **$5,069.6\ \mu\text{s}$**, whereas periodic detection ($K=10$) required **$565.3\ \mu\text{s}$** — an **$8.97\times$ lower latency penalty** for periodic detection. | **Validated** |

---

## 3. Project Architecture & Directory Layout

```text
CA2-Deadlock-Detection-Avoidance/
├── README.md                               # Project documentation, findings, and reproduction guide
├── requirements.txt                        # Dependencies (matplotlib >= 3.8.0)
├── src/                                    # Core algorithms and models (Phase 1–5)
│   ├── __init__.py
│   ├── config.py                           # BenchmarkConfig, SystemConfig, WorkloadConfig dataclasses
│   ├── models.py                           # Immutable SystemState, Request, SafetyResult, DetectionResult
│   ├── bankers_algorithm.py                # Safety Algorithm & Resource-Request Algorithm
│   ├── deadlock_detector.py                # Multi-Instance Deadlock Detection Algorithm
│   ├── workload_generator.py               # Systematic workload generator (Safe, Unsafe, Deadlocked, Sweeps)
│   └── benchmark.py                        # Performance benchmarking harness with time.perf_counter
├── tests/                                  # 233 Unit and Invariant Test Suites
│   ├── __init__.py
│   ├── test_models.py                      # 50 tests: SystemState validation, immutability, conservation
│   ├── test_bankers.py                     # 72 tests: Safety check, resource request, rollback, Silberschatz
│   ├── test_detector.py                    # 61 tests: Detection, unallocated processes, cycles, Silberschatz
│   ├── test_workload_generator.py          # 29 tests: Reproducibility, seed invariance, boundary generation
│   └── test_benchmark.py                   # 21 tests: Timing accuracy, warm-ups, statistics computation
├── scripts/
│   └── run_experiments.py                  # Full experiment runner, data processor, and report generator
└── results/                                # Submission-Ready Experimental Artifacts
    ├── raw/                                # Raw JSON execution logs (1,920 measured runs)
    │   ├── scaling_benchmark_raw.json
    │   ├── operational_overhead_raw.json
    │   └── capacity_sweep_raw.json
    ├── processed/                          # Aggregated CSV summaries with statistics
    │   ├── scaling_benchmark_summary.csv
    │   ├── operational_overhead_summary.csv
    │   └── capacity_sweep_summary.csv
    ├── figures/                            # 7 Publication-Quality Figures (300 DPI, Vector/PNG)
    │   ├── fig1_execution_time_vs_processes.png
    │   ├── fig2_execution_time_vs_resources.png
    │   ├── fig3_mean_vs_median_comparison.png
    │   ├── fig4_workload_type_comparison.png
    │   ├── fig5_scaling_complexity_O_mn2.png
    │   ├── fig6_operational_overhead_comparison.png
    │   └── fig7_safe_to_unsafe_boundary_sweep.png
    └── reports/                            # Comprehensive Academic Engineering Report
        └── performance_investigation_report.md
```

---

## 4. Algorithmic Implementations

### A. Deadlock Avoidance: Banker's Safety Algorithm
- **Location:** [src/bankers_algorithm.py](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/src/bankers_algorithm.py)
- **Mathematical Specification:**
  1. Let $Work = Available$ (deep copy) and $Finish[i] = False$ for all $i \in \{0, \dots, n-1\}$.
  2. Find an index $i$ such that $Finish[i] == False$ and $Need[i] \le Work$.
  3. If found: $Work \leftarrow Work + Allocation[i]$, $Finish[i] \leftarrow True$, append $P_i$ to $SafeSequence$, and repeat step 2.
  4. If no such $i$ exists: if all $Finish[i] == True$, return Safe; otherwise return Unsafe.
- **Resource-Request Algorithm:**
  - Validates $Request[i] \le Need[i]$ and $Request[i] \le Available$.
  - Simulates allocation: $Available \leftarrow Available - Request[i]$, $Allocation[i] \leftarrow Allocation[i] + Request[i]$, $Need[i] \leftarrow Need[i] - Request[i]$.
  - Runs Safety Algorithm. If safe, commits the allocation; if unsafe, **fully rolls back** to the exact pre-request state and raises an error or returns a denied status.

### B. Multi-Instance Deadlock Detection Algorithm
- **Location:** [src/deadlock_detector.py](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/src/deadlock_detector.py)
- **Mathematical Specification:**
  1. Let $Work = Available$ (deep copy).
  2. For $i = 0, \dots, n-1$:
     - If $Allocation[i] == 0$, $Finish[i] = True$;
     - Else $Finish[i] = False$.
  3. Find an index $i$ such that $Finish[i] == False$ and $Request[i] \le Work$.
  4. If found: $Work \leftarrow Work + Allocation[i]$, $Finish[i] \leftarrow True$, and repeat step 3.
  5. If no such $i$ exists: if all $Finish[i] == True$, system is **not deadlocked**; otherwise, all processes with $Finish[i] == False$ are **deadlocked**.
  6. **Separation of Concerns:** Uses $Request[n \times m]$ (actual outstanding requests), never $Need[n \times m]$.

---

## 5. Verification & Test Suite

The test suite covers core models, invariant enforcement, algorithmic correctness, boundary edge cases, and timing metrics:

```bash
# Run the complete test suite from CA2 directory:
python -m unittest discover -s tests -p "test_*.py" -v
```

### Test Suite Summary (233 / 233 Passed)
| Test Module | Coverage Focus | Test Count | Pass Rate |
| :--- | :--- | :---: | :---: |
| `tests/test_models.py` | Invariants, conservation, immutability, validation errors | 50 | 100% |
| `tests/test_bankers.py` | Safety check, requests, rollback, Silberschatz canonical tests | 72 | 100% |
| `tests/test_detector.py` | Multi-instance detection, zero allocation, cycles, deadlocks | 61 | 100% |
| `tests/test_workload_generator.py` | Reproducibility, seed consistency, boundary generation | 29 | 100% |
| `tests/test_benchmark.py` | Timing harness, warm-up separation, statistics calculations | 21 | 100% |
| **Total Test Suite** | **Comprehensive Full-System Verification** | **233** | **100%** |

---

## 6. How to Reproduce Experiments

### Prerequisites
- Python 3.10+ (tested on Python 3.14.7)
- Matplotlib 3.8.0+

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full experimental suite (benchmarks, data aggregation, plot rendering, report)
python scripts/run_experiments.py
```

The script will:
- Run 160 benchmark evaluations (1,920 measured runs with `time.perf_counter`).
- Output raw JSON files to `results/raw/`.
- Output summary CSV files to `results/processed/`.
- Generate 7 publication figures to `results/figures/`.
- Generate the comprehensive scientific report at `results/reports/performance_investigation_report.md`.

---

## 7. Experimental Results & Visualization Catalog

All generated figures are saved at 300 DPI in [results/figures/](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/):

1. **[Figure 1: Execution Time vs Process Count ($n$)](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig1_execution_time_vs_processes.png)**  
   *Depicts quadratic scaling curves for Banker's Algorithm and Deadlock Detection across $n \in [5, 100]$ for $m \in \{3, 5, 10, 20\}$.*
2. **[Figure 2: Execution Time vs Resource-Type Count ($m$)](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig2_execution_time_vs_resources.png)**  
   *Demonstrates linear scaling with respect to $m$ across constant process slices.*
3. **[Figure 3: Mean vs Median Execution Time Comparison](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig3_mean_vs_median_comparison.png)**  
   *Evaluates timing stability and skewness under OS thread scheduling and caching variations.*
4. **[Figure 4: Workload Characteristic Impact](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig4_workload_type_comparison.png)**  
   *Compares execution times across Safe, Unsafe, Deadlocked, and Random state topologies.*
5. **[Figure 5: Algorithmic Complexity Validation against $O(m \cdot n^2)$](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig5_scaling_complexity_O_mn2.png)**  
   *Empirical runtime plotted directly against theoretical compound variable $m \cdot n^2$ ($R^2 > 0.95$).*
6. **[Figure 6: Cumulative Operational Overhead Comparison](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig6_operational_overhead_comparison.png)**  
   *Contrasts Strategy A (Proactive Banker's check per request: $5,069.6\ \mu\text{s}$) with Strategy B (Periodic Detection at $K=10$: $565.3\ \mu\text{s}$), demonstrating an $8.97\times$ reduction in overhead.*
7. **[Figure 7: Safe-to-Unsafe Phase Boundary Sweep](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/figures/fig7_safe_to_unsafe_boundary_sweep.png)**  
   *Maps the abrupt transition from Unsafe to Safe as bottleneck pressure $\rho_{\max}$ contracts below the critical threshold.*

---

## 8. Academic Report & Documentation

The full 17-section academic performance investigation report is available at:  
👉 **[results/reports/performance_investigation_report.md](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA2-Deadlock-Detection-Avoidance/results/reports/performance_investigation_report.md)**

It provides comprehensive coverage of:
- Theoretical backgrounds and mathematical invariants.
- Hypotheses formulations and validation summaries.
- Benchmark methodology and timer isolation techniques.
- Comprehensive empirical data tables.
- Systems engineering trade-offs (CPU latency vs resource utilization).
- Threats to validity and limitations.
- Academic and real-world OS conclusions.

---

## 9. Academic Integrity & Repository Isolation

- **Clean Working Tree:** The parent repository and CA1 directory (`CA1-Four-Resource-Deadlock/`) remain completely unmodified (`git status` clean on tracked files).
- **Self-Contained Module:** All code, tests, benchmarks, results, and documentation for CA2 are strictly isolated inside `CA2-Deadlock-Detection-Avoidance/`.
