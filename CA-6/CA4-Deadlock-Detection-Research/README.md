# CA4 Research Project: Deadlock Detection Algorithm Performance Evaluation (Topic R13)

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Test Suite](https://img.shields.io/badge/tests-59%20passed-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-submission--ready-success.svg)]()

Continuous Assessment 4 (CA4) – Research Mini-Project Topic R13:  
**Performance Evaluation of Deadlock Detection Algorithms under Different Resource Allocation Patterns.**

---

## 1. Project Overview & Research Scope

Deadlock detection is a fundamental operating system and distributed systems problem. While theoretical asymptotic complexities are well established in classical literature, empirical detection latency in production runtimes depends heavily on **runtime resource allocation topologies**, **early-termination conditions**, and **underlying resource capacity semantics**.

This project provides an empirical and theoretical investigation comparing:
1. **Single-Instance Deadlock Detection:** Directed **Wait-For Graph (WFG)** construction and elementary cycle enumeration.
2. **Multi-Instance Deadlock Detection:** Vector-based **Work/Finish Reduction** algorithm (Silberschatz, Galvin & Gagne, *Operating System Concepts*, §8.6).

Across four distinct deterministic and stochastic allocation patterns:
- **Acyclic:** Directed Acyclic Graphs (DAGs) forming clean dependency chains without circular wait.
- **Circular:** Closed circular wait rings of controlled size $k = \min(N, M)$.
- **Mixed:** Heterogeneous systems isolating active deadlock cycles, transitively blocked processes, and independent safe cohorts.
- **Random:** Parameterized Monte Carlo allocations evaluating stochastic deadlock emergence.

---

## 2. Directory Structure

```text
CA4-Deadlock-Detection-Research/
├── docs/
│   ├── data_analysis.md              # Detailed statistical regressions & tables
│   ├── results_interpretation.md     # Research question & hypothesis evaluations
│   ├── limitations_and_validity.md   # Threats to validity & runtime noise analysis
│   └── phase5_completion_report.md   # Executive completion report
├── experiments/
│   ├── experiment_config.json        # Formal matrix dimensions, seeds, and repetitions
│   └── run_experiments.py            # Automated trial execution & logging runner
├── results/
│   ├── figures/                      # Publication-quality figures (6 PNGs)
│   ├── processed/                    # Aggregated tabular CSV summaries
│   │   ├── matrix_experiment_summary.csv
│   │   ├── representative_summary.csv
│   │   └── smoke_test_summary.csv
│   ├── raw/                          # Microsecond-level JSON execution logs
│   │   ├── matrix_experiment_raw.json
│   │   ├── representative_raw.json
│   │   └── smoke_test_raw.json
│   ├── matrix_execution_log.json     # Audit log of trial execution & platform telemetry
│   └── representative_execution_log.json
├── src/
│   ├── analysis/
│   │   └── generate_visualizations.py# Matplotlib figure generation suite
│   ├── detectors/
│   │   ├── wait_for_graph.py         # WFG builder & elementary cycle finder
│   │   └── multi_instance_detector.py# Silberschatz §8.6 Work/Finish reduction
│   ├── generators/
│   │   ├── acyclic_pattern.py        # Deterministic acyclic workload generator
│   │   ├── circular_pattern.py       # Deterministic circular wait generator
│   │   ├── mixed_pattern.py          # Three-cohort partitioned generator
│   │   └── random_pattern.py         # Stochastic Monte Carlo generator
│   ├── benchmark.py                  # Benchmarking engine with timing isolation
│   ├── config.py                     # Environment capture & configuration models
│   ├── ground_truth.py               # Canonical verification cases
│   └── models.py                     # Immutable SystemState & matrix invariants
├── tests/
│   ├── test_benchmark.py             # 11 unit tests covering engine & serialization
│   ├── test_generators.py            # 15 unit tests covering generators & topologies
│   ├── test_ground_truth.py          # 9 unit tests verifying canonical cases
│   ├── test_models.py                # 10 unit tests verifying matrix invariants
│   ├── test_multi_instance_detector.py# 6 unit tests verifying reduction mechanics
│   └── test_wait_for_graph.py        # 8 unit tests verifying WFG cycle detection
├── README.md                         # Primary project documentation
└── requirements.txt                  # Python dependencies (matplotlib, pandas, numpy, scipy)
```

---

## 3. Key Findings and Academic Summary

1. **Pattern Sensitivity:**  
   Algorithmic latency is dictated by early-termination behavior:
   - **Multi-Instance Reduction** terminates on round 1 in circular deadlocks ($59.99\,\mu\text{s}$ median), but incurs worst-case $O(M \cdot N^2)$ sequential reduction in acyclic states ($126.54\,\mu\text{s}$ median).
   - **Wait-For Graph** achieves rapid termination on acyclic DAGs ($97.76\,\mu\text{s}$ median), but incurs highest latency on circular deadlocks ($223.11\,\mu\text{s}$ median) due to cycle traversal and canonicalization.
2. **Empirical Process Scaling ($N$):**  
   - WFG circular detection exhibits super-linear scaling: $t \propto N^{1.216}$ ($R^2 = 0.968$).
   - Multi-instance circular detection exhibits sub-linear scaling: $t \propto N^{0.791}$ ($R^2 = 0.840$).
3. **Resource Vector Scaling ($M$):**  
   - Multi-instance reduction exhibits strong linear dependence on vector width $M$ ($\beta_M = 0.984, p < 10^{-14}$) during acyclic allocations.
   - WFG cycle traversal is largely invariant to $M$ ($\beta_M = 0.176, p = 0.350$) once graph edges are constructed.
4. **Model Incomparability:**  
   Single-instance WFG and multi-instance reduction address distinct mathematical resource models ($Total=1$ vs. $Total=5$) and must not be conflated as a direct competitive ranking.

---

## 4. Verification and Execution Instructions

### Running the Test Suite
```powershell
# From the CA4-Deadlock-Detection-Research directory:
& "C:\Users\Vanshika\AppData\Local\Programs\Python\Python314\python.exe" -m unittest discover -s tests -p "test_*.py"
```
**Output:** `Ran 59 tests in 0.359s (OK)`

### Regenerating Publication Visualizations
```powershell
& "C:\Users\Vanshika\AppData\Local\Programs\Python\Python314\python.exe" src/analysis/generate_visualizations.py
```
Outputs 6 high-resolution figures under `results/figures/`.

### Re-running Benchmark Trials (Non-Destructive)
```powershell
& "C:\Users\Vanshika\AppData\Local\Programs\Python\Python314\python.exe" experiments/run_experiments.py --representative-only
```
