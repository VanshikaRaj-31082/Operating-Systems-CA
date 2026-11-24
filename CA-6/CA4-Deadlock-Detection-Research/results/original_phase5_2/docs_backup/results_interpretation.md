# Research Findings and Results Interpretation: CA4 R13 (Phase 5.2 Final Audit Edition)

**Project:** `CA4-Deadlock-Detection-Research/`  
**Topic:** R13 – Performance Evaluation of Deadlock Detection Algorithms under Different Resource Allocation Patterns  

---

## 1. Addressing the Core Research Questions

### RQ1: How do resource allocation patterns affect detection latency?
**Empirical Evidence & Balanced Testing:**  
Allocation patterns fundamentally alter algorithmic execution paths:
1. **For Wait-For Graph (Single-Instance):**
   - The **Circular** pattern creates an active cycle of size $k = \min(N, M)$, triggering DFS path exploration, cycle canonicalization, and BFS blocked-process identification (mean median: $223.11\,\mu\text{s}$, peak $952.95\,\mu\text{s}$ at $N=100, M=20$).
   - The **Acyclic** pattern forms a linear DAG without cycles. Backtracking DFS terminates upon reaching sink nodes without cycle formation ($97.76\,\mu\text{s}$).
   - The **Mixed** pattern isolates a small cycle ($k=2$) alongside a safe cohort ($99.10\,\mu\text{s}$).
   - The **Random** pattern exhibits the lowest latency ($63.87\,\mu\text{s}$) due to sparse edge connectivity.
2. **For Multi-Instance Reduction:**
   - The **Circular** pattern causes available capacity to remain zero, and every deadlocked process requests more than available units. The outer search loop fails on round 1, terminating immediately in $O(N \cdot M)$ time ($59.99\,\mu\text{s}$).
   - Conversely, the **Acyclic** pattern forces the algorithm into sequential cascading reduction: one process finishes per outer loop iteration, requiring $N$ full scans and $O(M \cdot N^2)$ operations ($126.54\,\mu\text{s}$, peak $598.70\,\mu\text{s}$).

**Statistical Significance & Matched Post-Hoc Comparisons:**
- **Primary Matched Block Analysis (Friedman Test on 75 Matched Configurations):**
  - Single-Instance WFG: $\chi^2 = 132.760, df = 3, p = 1.37 \times 10^{-28}$
  - Multi-Instance Reduction: $\chi^2 = 122.520, df = 3, p = 2.21 \times 10^{-26}$
- **Primary Pairwise Paired Wilcoxon Tests (Bonferroni $\alpha = 0.008333$):**
  - In Multi-Instance Reduction, Acyclic reduction is significantly slower than Circular ($p = 1.18 \times 10^{-13}$), Mixed ($p = 5.28 \times 10^{-14}$), and Random ($p = 3.17 \times 10^{-13}$). Mixed is significantly slower than Circular ($p = 5.64 \times 10^{-4}$) and Random ($p = 5.61 \times 10^{-3}$). Only Circular vs. Random is not distinguishable ($p = 0.413$).
  - In Single-Instance WFG, Circular is significantly slower than Acyclic ($p = 2.69 \times 10^{-5}$), Mixed ($p = 5.91 \times 10^{-9}$), and Random ($p = 5.28 \times 10^{-14}$), while Random is significantly faster than Acyclic ($p = 5.67 \times 10^{-10}$) and Mixed ($p = 6.93 \times 10^{-10}$). Only Acyclic vs. Mixed is not distinguishable ($p = 0.0973$).
- **Supplementary Independent Kruskal-Wallis Tests:** Full dataset: Single-Instance $H = 29.113, p = 2.12 \times 10^{-6}$; Multi-Instance $H = 25.631, p = 1.14 \times 10^{-5}$. Balanced subset: Single-Instance $H = 20.960, p = 1.07 \times 10^{-4}$; Multi-Instance $H = 30.071, p = 1.33 \times 10^{-6}$.

---

### RQ2: How does process scaling ($N$) affect detection latency?
**Empirical Evidence & Model Consistency:**  
- **WFG Circular Scaling:** Both univariate ($\hat{\beta}_N = 1.2158, \text{SE}=0.0223, t=9.6914, df=98, p < 10^{-15}$) and multivariable models controlling for $M$ ($\hat{\beta}_N = 1.2158, \text{SE}=0.0190, t=11.3674, df=97, p < 10^{-16}$) confirm super-linear scaling ($\beta_N > 1.0$).
- *Crucial Theoretical Clarification:* In the circular generator, cycle length is $k = \min(N, M)$, which saturates at $k = M$ for **17 out of 20 experimental $(N, M)$ combinations (85.0%)**. Therefore, this super-linear scaling is **not** caused by an infinitely expanding cycle ring. Instead, it reflects:
  1. $O(N^2 \cdot M)$ graph construction,
  2. Exploring simple paths through expanding non-cycle process nodes ($N - k$ processes), and
  3. BFS reachability analysis to label blocked processes behind the cycle.
- **Multi-Instance Reduction:** Exhibits sub-linear scaling in circular deadlocks ($\hat{\beta}_N = 0.7912 \pm 0.0211$) due to immediate round-1 short-circuiting.

---

### RQ3: How does resource type scaling ($M$) affect detection latency?
**Empirical Evidence & Interaction Testing:**  
- Resource type count $M$ has a massive scaling effect on Multi-Instance Reduction in acyclic workloads ($\hat{\beta}_M = 0.9837 \pm 0.0493, t = 19.94$), confirming near-linear scaling with vector width.
- In contrast, WFG circular detection exhibits only minor resource scaling ($\hat{\beta}_M = 0.1756 \pm 0.0286$).
- A pooled interaction regression on acyclic workloads confirmed a statistically significant positive interaction term ($\hat{\beta}_{\text{interaction}} = 0.4160 \pm 0.0571, t_{\text{HC3}} = 7.28, p_{\text{HC3}} = 7.82 \times 10^{-12}$), robust to heteroscedasticity.

---

### RQ4: How do single-instance and multi-instance algorithms behave under their respective models?
**Model Segregation Invariant:**  
- **Wait-For Graph** is mathematically complete and sound **only** for single-instance models ($Total=1$).
- **Multi-Instance Reduction** operates over integer resource vectors ($Total=5$).
- Their execution latencies cannot be treated as a direct "head-to-head" ranking because they evaluate fundamentally different concurrency semantics.

---

### RQ5: Correctness of Deterministic Scenarios
All deterministic scenarios with independently established analytical ground truth were validated with **100% accuracy**:
- **Acyclic:** 200 / 200 trials correctly identified as deadlock-free (`is_deadlocked = False`).
- **Circular:** 200 / 200 trials correctly identified as deadlocked (`is_deadlocked = True`).
- **Mixed:** 150 / 150 trials correctly identified as deadlocked (`is_deadlocked = True`), with deadlocked and blocked cohorts properly separated.

---

### RQ6: What can and cannot be concluded from random workloads?
1. **What CAN be concluded:**
   - Under single-instance random workloads with allocation ratio 0.7 and request probability 0.5, **0 / 100 trials** resulted in deadlock. Single-instance resources with random allocation rarely form closed cycles by pure chance.
   - Under multi-instance random workloads (capacity 5), **72 / 100 trials (72.0%)** resulted in a detector-positive output.
2. **What CANNOT be concluded:**
   - The 72 positive outputs cannot be declared "confirmed deadlocks" against an external oracle because stochastic workloads lack an independent analytical ground truth. They are strictly reported as **detector-positive rates**.

---

## 2. Hypothesis Evaluation Matrix

| Hypothesis | Predicted Statement | Statistical Test & Empirical Result | Verdict |
| :--- | :--- | :--- | :---: |
| **H1: Pattern Sensitivity** | Allocation patterns significantly alter detection latency for both algorithms. | Primary Friedman test on matched configurations: Single-Instance $\chi^2 = 132.76, p = 1.37 \times 10^{-28}$; Multi-Instance $\chi^2 = 122.52, p = 2.21 \times 10^{-26}$. Pairwise Wilcoxon tests with Bonferroni correction confirm 5 out of 6 pairs are statistically distinguishable in both algorithms. | **SUPPORTED** |
| **H2: Super-Linear Process Scaling** | WFG cycle detection latency scales super-linearly with $N$ in cyclic workloads. | One-sided t-test on multivariable $\hat{\beta}_N = 1.2158 > 1.0$: $t = 11.3674, df=97, p < 10^{-16}$ (univariate: $t=9.6914, df=98, p < 10^{-15}$). Cycle size $k = \min(N, M)$ saturates at $k=M$ for 17 out of 20 configurations; super-linear scaling is driven by $O(N^2 M)$ construction + path exploration. | **SUPPORTED (Qualified)** |
| **H3: Multi-Instance Early Termination** | Multi-instance reduction detects circular deadlocks faster than complete acyclic reductions due to early loop exit. | Paired Wilcoxon signed-rank test on 100 exact $(N, M, \text{seed})$ pairs: $W = 177.0, p = 3.42 \times 10^{-16}$. Mechanism verified via trace analysis showing 1 pass vs. $N$ sequential passes. | **SUPPORTED** |
| **H4: Differential Resource Scaling** | Resource count $M$ has a significantly stronger scaling effect on multi-instance reduction than on WFG. | Formal interaction model on acyclic workloads with HC3 robust standard errors: $\hat{\beta}_{\ln(M) \times \text{is\_multi}} = 0.4160 \pm 0.0571$, $t_{\text{HC3}} = 7.28, p_{\text{HC3}} = 7.82 \times 10^{-12}$. | **SUPPORTED** |
