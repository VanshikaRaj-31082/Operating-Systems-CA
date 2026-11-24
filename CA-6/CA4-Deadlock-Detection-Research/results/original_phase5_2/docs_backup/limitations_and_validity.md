# Threats to Validity and Study Limitations: CA4 R13 (Revised & Validated)

**Project:** `CA4-Deadlock-Detection-Research/`  
**Topic:** R13 – Performance Evaluation of Deadlock Detection Algorithms under Different Resource Allocation Patterns  

---

## 1. Threats to Validity

### Threat 1: Dependence on Synthetic Workload Generators (Construct & External Validity)
- **Nature of the Threat:**  
  The experimental conclusions rest upon synthetic workload generators designed to construct canonical mathematical topologies: linear DAGs (`acyclic`), closed homogeneous rings (`circular`), partitioned cohorts (`mixed`), and uniform stochastic distributions (`random`).
- **Potential Bias:**  
  Real-world operating systems and database transaction engines exhibit complex, non-uniform access patterns, including hotspotting (Pareto / Zipfian distribution on specific locks), bursty lock acquisitions, short lock hold times, and hierarchical acquisition protocols. Synthetic generators may overestimate the prevalence of clean rings or underestimate lock contention skew.
- **Mitigation & Boundary:**  
  The synthetic models are designed strictly to isolate theoretical edge cases and verify asymptotic behavior under controlled variables ($N$, $M$). The findings represent algorithmic scaling boundaries rather than production throughput measurements.

### Threat 2: Runtime, OS, and Hardware Latency Jitter (Internal Validity)
- **Nature of the Threat:**  
  Microsecond-scale measurements ($10\text{--}900\,\mu\text{s}$) are susceptible to host system noise, including Windows thread scheduling quantum context switches, CPU frequency scaling (Intel Turbo Boost / SpeedStep), instruction cache warming, and Python CPython runtime overheads (garbage collection, GIL management).
- **Observed Evidence:**  
  In 14 out of 375 single-instance trials, the ratio $\frac{\text{Mean}}{\text{Median}}$ exceeded $1.5$, driven by occasional outlier spikes up to $952\,\mu\text{s}$ caused by CPU interrupts.
- **Mitigation:**  
  - 5 unmeasured warm-up iterations were executed before every trial to prime instruction caches and Python bytecode dispatch.
  - 30 repetitions were measured for each configuration.
  - Both mean and median metrics were recorded, with median utilized as the robust central tendency statistic throughout all scaling models.

---

## 2. Theoretical and Methodological Limitations

### Limitation 1: Backtracking Elementary Cycle Enumeration Complexity
- The implementation in `src/detectors/wait_for_graph.py` uses backtracking DFS rather than Johnson's cycle-finding algorithm.
- Johnson's algorithm actively manages vertex unblocking to achieve an asymptotic bound of $O((V + E)(C + 1))$ where $C$ is the cycle count.
- In contrast, simple backtracking DFS without Johnson's lookahead blocking can explore an **exponential number of simple paths**, even in graphs with zero cycles (or dense DAG components).
- Therefore, the measured WFG latency reflects both the graph density and the number of paths explored, rather than an optimal cycle-enumeration bound.

### Limitation 2: Circular Pattern Saturation ($k = \min(N, M)$)
- In `src/generators/circular_pattern.py`, cycle length $k$ is capped at $\min(N, M)$.
- In experimental configurations where $N \ge M$ (which includes $N \in [50, 100]$ with $M \le 20$), the cycle length saturates at $k = M$ and does not grow with $N$.
- Consequently, the observed process-scaling exponent $\hat{\beta}_N = 1.2158$ reflects the expanding $N$-node graph construction ($O(N^2 M)$) and path exploration over the non-cycle nodes ($N - k$), rather than an expanding cycle ring.

### Limitation 3: Incomparability of Resource Models
- Wait-For Graph (WFG) analysis is restricted to single-instance models ($Total[j] = 1$). Running WFG on multi-instance models is mathematically unsound.
- Multi-Instance reduction evaluates vector operations over integer capacities ($Total[j] = 5$).
- Because their operational semantics differ, execution times cannot be ranked directly against each other as competing solutions for the same problem. They address different concurrency regimes.

### Limitation 4: Generator Dimension Constraints
- The `mixed` generator requires $M \ge 4$ to fit its three independent process cohorts. Configurations with $M=3$ could not be executed for the mixed pattern, leaving 50 configurations unsupported out of the planned 800. These were properly logged rather than arbitrarily altered.
