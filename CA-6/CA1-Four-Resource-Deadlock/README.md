# Operating Systems CA-1: Four-Resource Deadlock Engineering Project
## Practical Simulation, Cycle Detection, and Havender's Prevention Protocol

**Course:** Operating Systems (Continuous Assessment 1)  
**Challenge:** Category D — Deadlock: Challenge D1 (Four-Resource Deadlock)  
**Reference Document:** `Activities-and-Assignments/CA1_Systems_Thinking_Challenge.md` (§11, Lines 547–567)  
**Environment:** Python 3.10+ (Standard Library Only — Zero external pip dependencies)  

---

## 1. Problem Overview: Challenge D1

In an enterprise data ingestion pipeline, four concurrent worker processes execute transactions requiring combinations of four non-shareable, single-unit system resources:

### The 4 Resources
1. **$R_1$ (Printer):** Dedicated hardware output device for physical audit logs.
2. **$R_2$ (Scanner):** Dedicated hardware input device for scanning physical barcodes.
3. **$R_3$ (Database Lock):** Exclusive transaction write-lock on central SQL ledger.
4. **$R_4$ (Network Resource):** Dedicated socket connection to a remote archival gateway.

### The 4 Processes & Circular Workload
- **$P_1$ (Audit Logger):** Requires $R_1$ (Printer), then requests $R_2$ (Scanner).
- **$P_2$ (Document Ingestion):** Requires $R_2$ (Scanner), then requests $R_3$ (Database Lock).
- **$P_3$ (Ledger Sync):** Requires $R_3$ (Database Lock), then requests $R_4$ (Network Resource).
- **$P_4$ (Remote Report Dispatcher):** Requires $R_4$ (Network Resource), then requests $R_1$ (Printer).

When executed concurrently under high load, all four processes acquire their first resource before any can acquire their second. This forms a closed circular wait dependency:
$$(P_1) \to [R_2] \to (P_2) \to [R_3] \to (P_3) \to [R_4] \to (P_4) \to [R_1] \to (P_1)$$

Because all resources are single-unit, this cycle is **both necessary and sufficient for deadlock**. All four processes freeze indefinitely.

---

## 2. Theoretical Foundations

### 2.1 The Four Coffman Conditions (Coffman et al., 1971)
Deadlock occurs if and only if all four conditions hold simultaneously:
1. **Mutual Exclusion:** Resources cannot be shared simultaneously. The printer, scanner, DB lock, and socket are strictly exclusive.
2. **Hold and Wait:** Each process holds one resource while waiting to acquire another held by another process.
3. **No Preemption:** The OS kernel cannot forcibly seize resources from a running process mid-transaction.
4. **Circular Wait:** A closed dependency chain exists ($P_1 \to P_2 \to P_3 \to P_4 \to P_1$).

### 2.2 Mathematical Justification: Deadlock Prevention via Total Ordering
To eliminate Circular Wait, we implement **Havender's Hierarchical Resource Ordering Protocol** (1968).

1. Define a global bijective ranking function $F: R \to \mathbb{N}$:
   $$F(R_1) = 1, \quad F(R_2) = 2, \quad F(R_3) = 3, \quad F(R_4) = 4$$
2. **The Invariant Rule:** A process holding resource $R_a$ may request resource $R_b$ if and only if:
   $$F(R_b) > F(R_a)$$
3. **Proof by Contradiction:**
   - Assume a deadlock cycle exists: $P_1 \to R_{j_1} \to P_2 \to R_{j_2} \dots \to P_k \to R_{j_k} \to P_1$.
   - For each hop along the cycle, the requested resource must have a strictly higher rank than the held resource:
     $$F(R_{j_1}) < F(R_{j_2}) < \dots < F(R_{j_k})$$
   - To close the cycle, $P_1$ must hold $R_{j_k}$ and request $R_{j_1}$, requiring:
     $$F(R_{j_k}) < F(R_{j_1})$$
   - Combining inequalities yields $F(R_{j_1}) < F(R_{j_1})$, a logical contradiction ($\bot$).
   - Therefore, the Resource Allocation Graph is strictly a **Directed Acyclic Graph (DAG)**. A DAG cannot contain cycles; hence, deadlock is mathematically impossible.

### 2.3 Critical Distinction: Deadlock Freedom $\neq$ Starvation Freedom
> **Important OS Principle:** Deadlock prevention invalidates circular wait, guaranteeing that the system as a whole makes progress (no total freeze). However, **it does not automatically guarantee starvation freedom for individual processes**.  
> If multiple processes frequently request low-ranked resources (such as $R_1$), a process waiting for $R_1$ (such as $P_4$) may suffer **indefinite postponement (starvation)** unless the underlying lock manager enforces fair FIFO acquisition queueing.

### 2.4 Simulation Level vs. Production Kernel Reality
- **User-Space Simulation:** Python threads blocked on `threading.Lock` simulate processes waiting on mutual exclusion primitives. The Windows/Linux operating system kernel remains healthy, responsive, and schedules other system processes normally.
- **Kernel-Level Deadlock:** True OS deadlock occurs when kernel dispatchers or interrupt handlers freeze on un-preemptible internal spinlocks, freezing hardware I/O and requiring a hardware reset.

---

## 3. Project Architecture & Module Responsibilities

```text
CA1-Four-Resource-Deadlock/
├── src/
│   ├── config.py                 # Ranks, workflow definitions, and timeouts
│   ├── models.py                 # Thread-safe Resource, Process, and RAG classes
│   ├── deadlock_detector.py      # 3-color DFS cycle detection engine
│   ├── simulation_naive.py       # Deterministic deadlock engine using threading.Barrier
│   ├── simulation_prevented.py   # Hierarchical resource acquisition engine
│   ├── visualizer.py             # ASCII RAG and cycle diagram renderer
│   └── runner.py                 # Multiprocessing supervisor with safe process-isolation
├── tests/
│   ├── test_rag.py               # Unit tests for thread-safe RAG edge mutations
│   ├── test_detector.py          # Unit tests for DFS cycle detection accuracy
│   └── test_prevention.py        # 20-run stress test proving 100% completion & 0 cycles
├── results/                      # Auto-generated verification traces and JSON metrics
├── screenshots/                  # Reserved for terminal capture images for Overleaf
├── README.md                     # This file
└── requirements.txt              # Standard library note
```

---

## 4. How to Run

### Step 1 — Run the Automated Test Suite
From the repository root:
```powershell
python -m unittest discover -s "CA1-Four-Resource-Deadlock/tests" -p "test_*.py"
```

### Step 2 — Execute the Master Demonstration Runner
```powershell
python "CA1-Four-Resource-Deadlock/src/runner.py"
```

The master runner executes:
1. **Phase 1 (Naive):** Spawns a child process, synchronizes all 4 threads using a barrier, reproduces the exact circular wait, captures the live cycle via DFS, logs the trace, and cleanly terminates the child process without freezing.
2. **Phase 2 (Prevented):** Executes the same workload under Havender's Total Ordering, demonstrating 100% task completion with 0 cycles.
3. **Phase 3 (Metrics):** Generates comparative telemetry and writes evidence files to `results/`.

---

## 5. Generated Evidence Files

The runner populates:
- [`results/naive_deadlock_trace.txt`](results/naive_deadlock_trace.txt): Millisecond log of barrier sync, lock blocking, RAG snapshot, and detected cycle.
- [`results/prevented_trace.txt`](results/prevented_trace.txt): Timestamped log of ordered acquisitions, task work execution, and release transitions.
- [`results/metrics_summary.json`](results/metrics_summary.json): Machine-readable JSON summary of completion rates, runtimes, and cycle counts for citation in the Overleaf report.

---

## 6. Honest Performance & Limitations Analysis

| Factor | Observation | Engineering Explanation |
|---|---|---|
| **Runtime Overhead** | Non-zero | Re-ordering and validating resource ranks requires sorting ($O(k \log k)$ for $k$ resources). |
| **Concurrency Penalty** | Moderate | Processes must acquire low-ranked resources early, holding them longer than strictly needed, which temporarily blocks competing threads. |
| **CPython GIL Effect** | Present | Python's Global Interpreter Lock serializes bytecode execution, providing simulated concurrency rather than multi-core parallel CPU execution. |
| **Timer Resolution** | Jitter (~1–15 ms) | Windows OS timer resolution introduces minor measurement noise in sub-second sleep intervals. |

