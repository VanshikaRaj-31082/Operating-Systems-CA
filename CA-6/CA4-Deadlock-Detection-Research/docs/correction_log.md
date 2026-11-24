# CA4 R13 Correction Log

This log documents all identified methodological issues, their theoretical and empirical causes, affected modules, executed corrections, and experiment regeneration tracking for Continuous Assessment 4 (CA4) Topic R13: **Performance Evaluation of Deadlock Detection Algorithms under Different Resource Allocation Patterns**.

---

## Issue Summary Matrix

| Issue ID | Identified Issue | Root Cause | Affected Files | Correction Applied | Experimental Regeneration Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **ISS-01** | Zero allocation in Single-Instance Random workloads | `int(cap * ratio)` for `cap=1` and `ratio=0.7` evaluates to 0, forcing `randint(0,0)=0`. Multi-instance logic also truncated uniform distribution. | `src/generators/random_pattern.py`, `tests/test_generators.py` | Implemented Binomial/Bernoulli allocation sampling where each resource unit has probability $p = \text{allocation\_ratio}$ of being allocated. Added full unit tests. | **Regenerated** (All Single-Instance & Multi-Instance Random workloads). |
| **ISS-02** | Misattributed Acyclic reduction step count in H3 | Generator assigns resource $j$ to process $j \bmod n$. When $n > m$, only $m$ processes hold resources. Detector finishes unallocated processes at initialization; thus reduction passes equal allocated process count ($m$), not $n$. | `docs/data_analysis.md`, `docs/results_interpretation.md`, `docs/final_report.tex` | Audited exact reduction step counts across matrix ($N, M$). Separated empirical timing difference from trace-based mechanistic explanation. | **Documentation & Trace Analysis Corrected** (Underlying states valid). |
| **ISS-03** | Unvalidated Random Workload Ground-Truth Labeling | Random workloads lack an external analytical oracle; detector-positive outputs were previously vulnerable to misinterpretation as accuracy. | `docs/data_analysis.md`, `docs/results_interpretation.md`, `docs/final_report.tex` | Formalized ground-truth policy: random workloads serve as performance workloads; status is strictly labeled as "detector-positive rate" without accuracy/precision claims. | **Documentation & Visualizations Corrected**. |
| **ISS-04** | Matched Experimental Configuration Alignment for H1 | The balanced subset ($M \ge 4$) shares identical $(N, M, \text{seed})$ tuples across patterns, requiring repeated-measures statistics rather than independent samples. | `src/analysis/run_statistical_analysis.py`, `docs/data_analysis.md`, `docs/results_interpretation.md`, `docs/final_report.tex` | Designated matched-block Friedman test ($\chi^2$) and Kendall's $W$ effect size as primary omnibus analysis; pairwise paired Wilcoxon tests with Bonferroni correction as primary post-hoc; Kruskal-Wallis as supplementary. | **Recalculated on Corrected Dataset**. |
| **ISS-05** | Cycle-Saturation Count Inconsistency for H2 | Circular cycle size $k = \min(N, M)$ saturates at $k=M$ whenever $N \ge M$. Out of 20 $(N, M)$ pairs, exactly 17 (85%) satisfy $N \ge M$. | `docs/data_analysis.md`, `docs/results_interpretation.md`, `docs/final_report.tex` | Corrected combination count to 17/20 (85%). Clarified that empirical scaling exponent $\beta_N = 1.2158$ reflects $O(N^2 M)$ graph construction + path exploration, not an expanding cycle ring. | **Documentation & Text Reconciled**. |
| **ISS-06** | Heteroscedasticity in Acyclic Interaction Model (H4) | Breusch-Pagan test ($LM=22.088, p=1.93\times 10^{-4}$) indicates heteroscedasticity in acyclic regression residuals. | `src/analysis/run_statistical_analysis.py`, `docs/data_analysis.md`, `docs/final_report.tex` | Applied HC3 heteroscedasticity-robust standard errors and confidence intervals. Confirmed interaction term remains statistically significant ($p_{\text{HC3}} = 7.82\times 10^{-12}$). | **Recalculated with HC3 Robust SEs**. |

---

## Detailed Audit Records

### Issue 1: Random Workload Allocation Sampling Defect
- **Condition:** In `src/generators/random_pattern.py`, line 99: `units_to_allocate = rng.randint(0, int(cap * allocation_ratio))`.
- **Impact:** For $cap = 1$ and $allocation\_ratio = 0.7$, `int(1 * 0.7) = 0`, forcing `randint(0, 0) == 0`. Hence, all single-instance random trials allocated exactly zero resources. The WFG detector processed empty graphs with 0 edges, yielding an artificial 0% deadlock rate. In multi-instance models with $cap = 5$, `int(5 * 0.7) = 3`, choosing uniformly between 0 and 3 units (expected mean 1.5 units, or 30% of capacity) rather than the intended 70% expectation (3.5 units).
- **Remediation:** Replaced with an exact Binomial allocation model: for each unit of capacity $c \in \{1, \dots, T_j\}$, perform an independent Bernoulli trial with probability $p = \text{allocation\_ratio}$. Each allocated unit is assigned to a process chosen uniformly at random using the isolated seed instance. Strict conservation ($V_j + \sum_i A_{i,j} = T_j$) is preserved.

### Issue 2: Acyclic Workload Reduction Step Trace Analysis
- **Condition:** In `src/generators/acyclic_pattern.py`, resources are allocated via `allocation[j % n][j] = total[j]`. When $n > m$, only $m$ distinct processes receive non-zero allocations.
- **Impact:** In the multi-instance reduction algorithm, Step 2 marks all unallocated processes ($\mathbf{Allocation}[i] == \mathbf{0}$) as $\mathbf{Finish}[i] = \text{True}$ immediately. Consequently, the number of process completion events recorded in `MultiInstanceResult.trace` is exactly $\min(n, m)$, not $n$.
- **Remediation:** Audited exact trace counts across all $(N, M)$ configurations. Documented that circular workloads terminate on round 1 with 0 successful reductions, whereas acyclic workloads execute $\min(n, m)$ successful cascading reductions. Retained timing comparisons while correcting mechanistic trace claims.
