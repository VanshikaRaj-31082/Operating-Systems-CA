# CA-3: OS Design & Debugging Challenge
## Challenge D1: Two-Lock Deadlock Diagnosis, Remediation, and Technical Defence

**Course:** Operating Systems  
**Component:** Continuous Assessment 3 (10 Marks)  
**Track:** Concurrency, Synchronization & Deadlocks  
**Author / Candidate:** Second-Year AI/ML Engineering Student  
**System Environment:** Windows 11 (64-bit) | Python 3.14.7 | Pure Standard Library  

---

## 1. Project Overview

This project provides an end-to-end engineering solution for **CA-3 Category D (Deadlock), Challenge D1: Two-Lock Deadlock**.

The investigation progresses across five formal engineering phases:
1. **Phase 1 (Reproduction):** Deterministic reproduction of the two-lock deadlock under concurrent thread execution.
2. **Phase 2 (Root Cause Analysis):** Detailed diagnosis mapping the failure to the four Coffman conditions, complete with Resource Allocation Graph (RAG) and Wait-For Graph (WFG) derivations.
3. **Phase 3 (Solution Design & Alternative Analysis):** In-depth comparative design of **Hierarchical Resource Ordering** versus **Timeout-Based Backoff & Retry**.
4. **Phase 4 (Implementation & Validation):** Clean Python 3 implementation of the selected hierarchical ordering fix, backed by an automated 7-part test suite with a 100-iteration stress test.
5. **Phase 5 (Technical Defence & Submission Audit):** Formal viva defense guide, precise answers to 10 core questions, and rubric-mapped verification checklist.

---

## 2. Directory Structure

```text
CA3-Two-Lock-Deadlock/
├── README.md                                    # This project navigation guide
│
├── src/                                         # Source Code Modules
│   ├── deadlock_demo.py                         # 100% UNMODIFIED baseline failure witness
│   └── deadlock_prevented.py                    # Remediated Hierarchical Resource Ordering
│
├── tests/                                       # Automated Verification Suite
│   ├── __init__.py                              # Test package marker
│   └── test_deadlock_prevention.py              # 7 automated tests (100-run stress test included)
│
├── diagrams/                                    # Publication Graphics & Graph Sources
│   ├── deadlock_graphs.png                      # Side-by-side RAG & WFG visualization (300 DPI)
│   ├── resource_allocation_graph.png            # Standalone Resource Allocation Graph (300 DPI)
│   ├── wait_for_graph.png                       # Standalone Wait-For Graph (300 DPI)
│   ├── resource_allocation_graph.mmd            # Raw Mermaid source for RAG
│   ├── wait_for_graph.mmd                       # Raw Mermaid source for WFG
│   ├── thread_execution_trace.mmd               # Raw Mermaid sequence diagram
│   └── generate_diagrams.py                     # Python script to regenerate figures
│
└── docs/                                        # Comprehensive Academic Reports
    ├── root_cause_analysis.md                   # Phase 2: RCA, Coffman proofs, interleaving, RAG/WFG
    ├── solution_design.md                       # Phase 3: Detailed architecture of Strategies 1 & 2
    ├── strategy_comparison.md                   # Phase 3: Trade-off matrix & selection justification
    ├── implementation_and_validation.md         # Phase 4: Verification, 100-run stress, comparison
    ├── technical_defence.md                     # Phase 5: 10 viva questions and verified answers
    └── final_submission_checklist.md            # Phase 5: Submission audit and rubric verification
```

---

## 3. Quick Start & Reproduction Commands

All core code and tests rely strictly on the **Python Standard Library** (`threading`, `multiprocessing`, `time`, `unittest`). No external package installations are required.

### 1. Run the Baseline Failure Witness
Demonstrates the two-lock deadlock; the parent watchdog detects indefinite blocking and terminates the process at 3.0 seconds:
```powershell
python src/deadlock_demo.py
```

### 2. Run the Remediated Hierarchical Ordering Implementation
Demonstrates clean, unblocked concurrent execution in milliseconds with verified data integrity:
```powershell
python src/deadlock_prevented.py
```

### 3. Execute the Automated Test Suite
Executes all 7 unit, stress, and invariant tests:
```powershell
python -m unittest tests/test_deadlock_prevention.py -v
```

### 4. Regenerate Diagram Figures
Generates the 300 DPI publication-grade figures in `diagrams/`:
```powershell
python diagrams/generate_diagrams.py
```

---

## 4. Key Findings & Empirical Results

| Metric | Baseline Implementation (`deadlock_demo.py`) | Corrected Implementation (`deadlock_prevented.py`) |
| :--- | :--- | :--- |
| **Acquisition Order** | Asymmetric: $T_1: \langle A, B \rangle$ vs $T_2: \langle B, A \rangle$ | Strict Hierarchical: $T_1: \langle A, B \rangle$ and $T_2: \langle A, B \rangle$ |
| **Deadlock Rate** | **100%** (Permant circular wait) | **0%** (0 deadlocks across 100 stress runs) |
| **Execution Duration** | 3.1648 s (Hangs until watchdog timeout) | 0.00628 s (Direct unhindered execution) |
| **Thread Completion** | Blocked indefinitely in mutex wait-queue | Clean exit and join for both threads |
| **Termination Method** | Forced `process.terminate()` | Clean return of thread functions |
| **Automated Tests** | Fails / Hangs | **7 / 7 passed in 0.034s** |

---

## 5. Academic Documentation Index

- **Root Cause Analysis:** [`docs/root_cause_analysis.md`](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA3-Two-Lock-Deadlock/docs/root_cause_analysis.md)
- **Solution Design:** [`docs/solution_design.md`](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA3-Two-Lock-Deadlock/docs/solution_design.md)
- **Strategy Comparison:** [`docs/strategy_comparison.md`](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA3-Two-Lock-Deadlock/docs/strategy_comparison.md)
- **Implementation & Validation:** [`docs/implementation_and_validation.md`](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA3-Two-Lock-Deadlock/docs/implementation_and_validation.md)
- **Technical Defence & Viva Prep:** [`docs/technical_defence.md`](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA3-Two-Lock-Deadlock/docs/technical_defence.md)
- **Submission Checklist:** [`docs/final_submission_checklist.md`](file:///c:/Users/Vanshika/Downloads/Academics/OS%20cloned/Operating-System-Concepts/CA3-Two-Lock-Deadlock/docs/final_submission_checklist.md)
