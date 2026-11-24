# Detailed Data Analysis: CA4 R13 Benchmark Matrix (Phase 5.2 Integrity Audit Edition)

**Research Topic:** R13 – Performance Evaluation of Deadlock Detection Algorithms under Different Resource Allocation Patterns  
**Data Sources:**
- `results/processed/matrix_experiment_summary.csv` (750 completed trial summaries)
- `results/raw/matrix_experiment_raw.json` (22,500 individual measured repetition timings)
- `results/matrix_execution_log.json` (Execution environment, platform telemetry, and unsupported trial records)

---

## 1. Experimental Matrix & Execution Audit

### Parameter Space and Sample Distribution
The benchmark matrix evaluated five process scaling levels ($N \in [5, 10, 20, 50, 100]$), four resource type levels ($M \in [3, 5, 10, 20]$), four allocation patterns (`acyclic`, `circular`, `random`, `mixed`), two resource models (`single_instance` mapped to Wait-For Graph, `multi_instance` mapped to Multi-Instance Reduction), and five deterministic seeds ($S \in [101, 202, 303, 404, 505]$).

- **Planned Configurations:** $5 \times 4 \times 4 \times 2 \times 5 = 800$ configurations.
- **Completed Configurations:** 750 configurations (93.75%).
- **Unsupported Configurations:** 50 configurations (6.25%).
- **Failed / Erroneous Configurations:** 0 (0.0%).
- **Timed Repetitions per Configuration:** 30 isolated measurements.
- **Total Algorithmic Executions:** 22,500 timed + 3,750 warm-up + 750 pre-validation = 27,000 invocations.

### Verification of Unsupported Configurations
All 50 unsupported trials correspond strictly to the condition:
$$\text{Pattern} = \text{mixed} \quad \wedge \quad M = 3$$
Across all $N \in [5, 10, 20, 50, 100]$, both resource models, and all 5 seeds ($5 \times 2 \times 5 = 50$).

**Mathematical Cause:**  
The `generate_mixed_workload` generator partitions the system into three distinct cohorts:
1. Deadlock Cycle Cohort (size $k = 2$)
2. Blocked Cohort (size $b = 1$)
3. Independent Safe Cohort (size $s \ge 1$)

Assigning distinct, non-conflicting allocations to ensure that the safe cohort can proceed while the deadlocked cycle remains unresolvable requires:
$$M \ge k + b + 1 = 2 + 1 + 1 = 4$$
When $M = 3 < 4$, the required cohort isolation cannot be satisfied without violating the invariant. Rather than silently mutating $M$ or compromising workload semantics, the benchmark engine logged each trial with reason: `m (3) must be >= 4 to fit distinct resource allocations`.

---

## 2. Theoretical Complexity vs. Empirical Findings

### A. Wait-For Graph (WFG) Detector
1. **Graph Construction Overhead:**  
   To build the adjacency list from matrices `Request` and `Allocation`, the algorithm checks whether process $P_i$ has an unsatisfied request for resource $k$, and finds all other processes $P_j$ holding an allocation of $k$. In a graph without self-loops where processes may hold and request multiple resources, the general edge bound is $E \le N(N - 1)$.
   $$\text{Construction Complexity} = O(N^2 \cdot M)$$
2. **Cycle Existence vs. Elementary Cycle Enumeration:**  
   - **Simple Cycle Existence:** Testing whether at least one cycle exists via ordinary DFS requires $O(V + E)$ time, where $V = N$ and $E \le N(N - 1)$.
   - **Backtracking Elementary Cycle Enumeration:** The implementation in `src/detectors/wait_for_graph.py` (`find_elementary_cycles()`) uses backtracking DFS to find and record every simple cycle. **This is NOT Johnson's cycle-finding algorithm**, which achieves $O((V + E)(C + 1))$ by actively managing vertex unblocking. Instead, simple backtracking DFS can explore an exponential number of simple paths even in graphs with zero cycles (or dense DAG components).
   - Consequently, WFG execution latency depends heavily on the overall **graph topology and the total number of simple paths explored**, rather than strictly the number of cycles returned.
3. **Exact Cycle Length Saturation Invariant:**  
   In `src/generators/circular_pattern.py`, cycle length is defined as $k = \min(N, M)$. Across the 20 total $(N, M)$ parameter pairs:
   - **17 out of 20 pairs (85.0%)** satisfy $N \ge M$, where cycle size saturates at $k = M$ and **does not grow with $N$**.
   - Only **3 out of 20 pairs (15.0%)** satisfy $N < M$: specifically $(5, 10)$, $(5, 20)$, and $(10, 20)$.  
   Therefore, the empirical multivariable process-scaling exponent $\hat{\beta}_N = 1.2158$ reflects the combined real-world runtime of $O(N^2 M)$ graph construction, DFS path stack management, and cache dynamics across $N \in [5, 100]$, rather than an infinitely expanding cycle ring or asymptotic worst-case bounds.

### B. Multi-Instance Deadlock Detector (Work/Finish Reduction)
1. **Theoretical Worst-Case:**  
   The Silberschatz §8.6 algorithm maintains a `Work` vector (length $M$) and a `Finish` boolean vector (length $N$). In each round, it scans up to $N$ processes, performing an $M$-element vector comparison ($Request[i] \le Work$). In the worst case (where exactly one process finishes per outer loop), it performs $N + (N-1) + \dots + 1 = \frac{N(N+1)}{2}$ vector comparisons:
   $$\text{Worst-Case Complexity} = O(M \cdot N^2)$$
2. **Empirical Behavior on Workloads:**
   - **Circular Deadlock (Best-Case Short-Circuit):** In circular deadlock scenarios, available capacity is zero ($Available = [0, \dots, 0]$), and all active processes have requests exceeding available resources. On the very first pass of the outer loop, zero processes can be satisfied. The algorithm terminates immediately in $O(N \cdot M)$ time:
     $$\text{Circular Multi-Instance Median:} \quad 59.99\,\mu\text{s (mean across all trials)}, \quad \text{Scaling:} \quad t \propto N^{0.791} \quad (R^2 = 0.840)$$
   - **Acyclic Workload (Cascading Reduction):** In acyclic workloads, processes terminate sequentially from the terminal process backwards. The algorithm must execute $N$ sequential passes, each searching through the remaining processes:
     $$\text{Acyclic Multi-Instance Median:} \quad 126.54\,\mu\text{s}, \quad \text{Scaling:} \quad t \propto M^{0.984} \quad (R^2 = 0.460)$$

---

## 3. Comprehensive Summary Statistics Table

The table below summarizes the empirical detection metrics across all 750 configurations, grouped by resource model and allocation pattern:

| Resource Model | Workload Pattern | Completed Trials | Mean of Medians ($\mu\text{s}$) | Min Median ($\mu\text{s}$) | Max Median ($\mu\text{s}$) | Mean Sample StdDev ($\mu\text{s}$) | Verified Correctness | Detector-Positive Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Single-Instance (WFG)** | Acyclic | 100 | 97.76 | 11.60 | 319.65 | 35.04 | 100 / 100 (100%) | 0.0% (0 / 100) |
| **Single-Instance (WFG)** | Circular | 100 | 223.11 | 15.30 | 952.95 | 47.80 | 100 / 100 (100%) | 100.0% (100 / 100) |
| **Single-Instance (WFG)** | Mixed | 75 | 99.10 | 14.05 | 388.30 | 43.39 | 75 / 75 (100%) | 100.0% (75 / 75) |
| **Single-Instance (WFG)** | Random | 100 | 63.87 | 9.50 | 430.00 | 45.09 | Unverified | 0.0% (0 / 100) |
| **Multi-Instance (Reduction)** | Acyclic | 100 | 126.54 | 14.75 | 598.70 | 21.44 | 100 / 100 (100%) | 0.0% (0 / 100) |
| **Multi-Instance (Reduction)** | Circular | 100 | 59.99 | 8.00 | 356.50 | 9.88 | 100 / 100 (100%) | 100.0% (100 / 100) |
| **Multi-Instance (Reduction)** | Mixed | 75 | 76.67 | 14.00 | 259.70 | 10.59 | 75 / 75 (100%) | 100.0% (75 / 75) |
| **Multi-Instance (Reduction)** | Random | 100 | 56.36 | 8.50 | 258.95 | 4.66 | Unverified | 72.0% (72 / 100) |

*(Note: Standard deviations are expressed in microseconds ($\mu\text{s}$), not seconds).*

---

## 4. Phase 5.2 Statistical Integrity Audits: H1–H4

### A. Hypothesis H1: Matched Experimental Configurations & Post-Hoc Tests
The balanced subset of configurations ($M \in [5, 10, 20]$) contains exactly $N=75$ configurations for each of the four allocation patterns, matched by identical $(N, M, \text{seed})$ blocks:

1. **Primary Omnibus Analysis (Friedman Test on 75 Matched Blocks):**
   - **Single-Instance (WFG):** Friedman $\chi^2 = 132.760, df = 3, p = 1.37 \times 10^{-28}$
   - **Multi-Instance (Reduction):** Friedman $\chi^2 = 122.520, df = 3, p = 2.21 \times 10^{-26}$
   - *Interpretation:* When controlling for experimental blocks $(N, M, \text{seed})$, allocation topology has a profound, statistically significant effect on detection latency across both algorithms.

2. **Primary Pairwise Post-Hoc Analysis (Paired Wilcoxon Signed-Rank Tests with Bonferroni Correction, $\alpha = \frac{0.05}{6} = 0.008333$):**
   - **Single-Instance (WFG, $n=75$ pairs):**
     - Acyclic vs. Circular: $W = 630.0, p = 2.69 \times 10^{-5}$ (**Significant**, Circular > Acyclic)
     - Acyclic vs. Mixed: $W = 1111.0, p = 0.0973$ (Not significant)
     - Acyclic vs. Random: $W = 251.0, p = 5.67 \times 10^{-10}$ (**Significant**, Acyclic > Random)
     - Circular vs. Mixed: $W = 323.0, p = 5.91 \times 10^{-9}$ (**Significant**, Circular > Mixed)
     - Circular vs. Random: $W = 0.0, p = 5.28 \times 10^{-14}$ (**Significant**, Circular > Random)
     - Mixed vs. Random: $W = 257.0, p = 6.93 \times 10^{-10}$ (**Significant**, Mixed > Random)
     *(Result: In WFG, 5 out of 6 pairwise comparisons are statistically significant; only Acyclic vs. Mixed is not distinguishable).*
   - **Multi-Instance (Reduction, $n=75$ pairs):**
     - Acyclic vs. Circular: $W = 20.0, p = 1.18 \times 10^{-13}$ (**Significant**, Acyclic > Circular)
     - Acyclic vs. Mixed: $W = 0.0, p = 5.28 \times 10^{-14}$ (**Significant**, Acyclic > Mixed)
     - Acyclic vs. Random: $W = 45.0, p = 3.17 \times 10^{-13}$ (**Significant**, Acyclic > Random)
     - Circular vs. Mixed: $W = 772.0, p = 5.64 \times 10^{-4}$ (**Significant**, Mixed > Circular)
     - Circular vs. Random: $W = 1270.0, p = 0.413$ (Not significant)
     - Mixed vs. Random: $W = 900.5, p = 5.61 \times 10^{-3}$ (**Significant**, Mixed > Random)
     *(Result: In Multi-Instance, 5 out of 6 comparisons are statistically significant; only Circular vs. Random is not distinguishable).*

3. **Supplementary Independent-Samples Analyses (Kruskal-Wallis):**
   - Single-Instance WFG: Full dataset $H = 29.113$ ($p = 2.12 \times 10^{-6}$); Balanced subset $H = 20.960$ ($p = 1.07 \times 10^{-4}$).
   - Multi-Instance Reduction: Full dataset $H = 25.631$ ($p = 1.14 \times 10^{-5}$); Balanced subset $H = 30.071$ ($p = 1.33 \times 10^{-6}$).

*Conclusion for H1:* **SUPPORTED.**

---

### B. Hypothesis H2: Cycle Saturation Count & Model Consistency
1. **Univariate Model:** $\ln(\text{Median}) = a + \beta_N \ln(N)$
   - $\hat{\beta}_N = 1.2158, \text{SE} = 0.0223, 95\%\text{ CI} = [1.1716, 1.2600], df = 98$
   - One-sided test ($H_1: \beta_N > 1.0$): $t = 9.6914, p = 3.33 \times 10^{-16}, R^2 = 0.9682$
2. **Multivariable Model (Primary):** $\ln(\text{Median}) = \beta_0 + \beta_N \ln(N) + \beta_M \ln(M)$
   - $\hat{\beta}_N = 1.2158, \text{SE} = 0.0190, 95\%\text{ CI} = [1.1781, 1.2535], df = 97$
   - $\hat{\beta}_M = 0.1756, \text{SE} = 0.0286, 95\%\text{ CI} = [0.1189, 0.2323]$
   - One-sided test ($H_1: \beta_N > 1.0$): $t = 11.3674, p < 1.00 \times 10^{-16}, R^2 = 0.9771$

*Conclusion for H2:* **SUPPORTED (with qualification that cycle length $k = \min(N, M)$ saturates at $k=M$ for 17 out of 20 combinations).**

---

### C. Hypothesis H3: Pairing Validity & Mechanistic Distinction
- **Pairing:** Exactly 100 matching pairs verified across identical $(N, M, \text{seed})$ tuples.
- **Statistical Significance:** Paired Wilcoxon signed-rank test confirmed circular detection latency is significantly lower than acyclic: $W = 177.0, p = 3.42 \times 10^{-16}$.
- **Mechanistic Verification:** Algorithmic trace analysis of `MultiInstanceResult.trace` confirms that in Circular workloads, 0 processes are satisfiable on pass 1, terminating immediately in 1 scan (trace length = 2); in Acyclic workloads, $N$ sequential passes occur (trace length = $N + 2$). Empirical timing demonstrates the latency difference, while trace analysis proves the early-termination mechanism.

*Conclusion for H3:* **SUPPORTED.**

---

### D. Hypothesis H4: Heteroscedasticity Diagnostics & Robust SE (HC3)
To ensure the acyclic interaction model does not violate homoscedasticity assumptions, diagnostic checks and heteroscedasticity-robust standard errors were calculated:

1. **Heteroscedasticity Diagnostic:**
   - Breusch-Pagan Test: $LM = 22.088, df = 4, p = 1.93 \times 10^{-4}$.
   - Statistically significant heteroscedasticity is present ($p < 0.05$), confirming that classical OLS standard errors may be biased and that robust estimation is required.
2. **OLS vs. HC3 Robust Estimates Table:**

| Variable | $\hat{\beta}$ | $\text{SE}_{\text{OLS}}$ | $95\%\text{ CI}_{\text{OLS}}$ | $p_{\text{OLS}}$ | $\text{SE}_{\text{HC3}}$ | $95\%\text{ CI}_{\text{HC3}}$ | $p_{\text{HC3}}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Intercept** | $0.8206$ | $0.1101$ | [$0.6035, 1.0376$] | $2.87 \times 10^{-12}$ | $0.0782$ | [$0.6664, 0.9747$] | $< 1.0 \times 10^{-16}$ |
| **is_multi** | $-0.6819$ | $0.1286$ | [$-0.9354, -0.4283$] | $3.08 \times 10^{-7}$ | $0.1078$ | [$-0.8945, -0.4692$] | $1.69 \times 10^{-9}$ |
| **log_N** | $0.7144$ | $0.0201$ | [$0.6747, 0.7541$] | $< 1.0 \times 10^{-16}$ | $0.0187$ | [$0.6775, 0.7513$] | $< 1.0 \times 10^{-16}$ |
| **log_M** | $0.5676$ | $0.0428$ | [$0.4833, 0.6520$] | $< 1.0 \times 10^{-16}$ | $0.0344$ | [$0.4998, 0.6355$] | $< 1.0 \times 10^{-16}$ |
| **log_M $\times$ is_multi** | $0.4160$ | $0.0605$ | [$0.2967, 0.5353$] | $8.06 \times 10^{-11}$ | $0.0571$ | [$0.3034, 0.5287$] | $7.82 \times 10^{-12}$ |

*Conclusion for H4:* **SUPPORTED.** The interaction term remains positive and highly statistically significant under HC3 heteroscedasticity-robust standard errors ($t_{\text{HC3}} = 7.28, p_{\text{HC3}} = 7.82 \times 10^{-12}$), confirming that resource-count scaling is formally and significantly stronger in multi-instance reduction than in single-instance WFG.
