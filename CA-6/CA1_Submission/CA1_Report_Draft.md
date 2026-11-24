# Operating Systems – Continuous Assessment 1 (CA-1)
## OS Systems Thinking Challenge: Engineering Decision Report

**Course:** Operating Systems  
**Weightage:** 10 Marks  
**Assessment Nature:** Scenario-Based / Analytical / Engineering Decision-Oriented  

---

### Student & Challenge Metadata

| Metadata Field | Student Details |
|---|---|
| **Student Name** | [Enter Full Name] |
| **Registration / Roll No.** | [Enter Roll Number] |
| **Degree / Specialization** | B.Tech – Computer Science & Engineering (AI / ML) |
| **Year / Semester** | 2nd Year / Semester IV |
| **Assigned Challenge ID** | `[NEEDS FACULTY CONFIRMATION — e.g., Challenge B1, C1, D1]` |
| **Challenge Title** | `[NEEDS FACULTY CONFIRMATION — Title of Assigned Scenario]` |
| **Date of Submission** | `[Enter Date]` |

---

## A. Scenario Understanding

> **Official Instruction:** Briefly restate the assigned computing problem or system situation in your own words. Clearly describe the operational symptoms, user complaints, and observed computing bottlenecks without jumping directly to algorithms.

`[TO BE FILLED: 1–2 paragraphs restating the confirmed scenario in your own words. Detail the workload context, system environment, and observed performance or correctness degradation.]`

---

## B. OS Concept Identification

> **Official Instruction:** Identify the specific Operating System subsystem and concept(s) involved. Explain explicitly *why* this represents an operating-system problem rather than a syntax, network, or application-level logic error. Identify and discard irrelevant distractions.

- **Primary OS Subsystem:** `[e.g., Process Management & CPU Scheduling / Synchronization / Memory Management / Storage & I/O]`
- **Core OS Concepts:** `[e.g., Preemptive Scheduling, Quantum Expiry, Lock Contention, Race Condition, External Fragmentation, Thrashing]`
- **Contextual Reasoning:** `[Explain why the observed symptoms point directly to this OS mechanism and why application-level workarounds cannot resolve it.]`
- **Distractions Discarded:** `[Identify any superficial symptoms that are merely consequences rather than the core OS problem.]`

---

## C. System Model

> **Official Instruction:** Convert the scenario into an appropriate, rigorous technical model. Depending on the scenario, construct a process table, execution trace, state machine, Resource Allocation Graph (RAG), Gantt chart, memory allocation map, or mathematical representation.

```text
[INSERT ASCII, MERMAID, OR SCHEMATIC SYSTEM MODEL HERE]
Examples:
- CPU Scheduling: Process arrival, burst lengths, priority table, Gantt timeline
- Concurrency: Thread interleaving trace, shared memory state, critical section boundaries
- Deadlock: Resource Allocation Graph (Nodes: Processes, Resources; Edges: Request, Assignment)
- Memory: Logical-to-physical address mapping, free list blocks, fragmentation visualization
```

*Model Narrative:*  
`[Provide a brief technical explanation detailing the states, transitions, resource relationships, or queues represented in the model above.]`

---

## D. Constraints and Assumptions

> **Official Instruction:** Make all engineering boundaries, workload properties, and system constraints explicit.

### 1. System & Hardware Constraints
- **Processor Architecture:** `[e.g., Single-core / Multi-core, Symmetric Multi-Processing]`
- **Memory & Storage:** `[e.g., Limited physical RAM, cache hierarchy, storage medium (SSD/HDD)]`
- **Operating Environment:** `[e.g., Interactive desktop, server backend, embedded real-time]`

### 2. Workload Characteristics
- **Process Types:** `[e.g., Interactive/I/O-bound tasks vs CPU-heavy batch computations]`
- **Arrival & Burst Patterns:** `[e.g., Poisson arrivals, bursty requests, static job set]`
- **Concurrency Intensity:** `[e.g., Number of competing threads/processes, request rates]`

### 3. Engineering Assumptions
- `[Assumption 1: e.g., Context-switch overhead is non-negligible]`
- `[Assumption 2: e.g., Preemption is supported by the kernel]`
- `[Assumption 3: e.g., Resource requests are bounded and non-preemptible]`

---

## E. Alternative Solutions

> **Official Instruction:** Analyze at least two plausible operating-system mechanisms that could theoretically address the problem. For each alternative, describe how it operates, why it is applicable, its advantages, and its disadvantages under the stated constraints.

### Alternative 1: `[Name of Mechanism 1 — e.g., First-Come First-Served (FCFS) / Mutex Lock / First Fit]`
- **Operational Principle:** `[How the mechanism functions within the kernel]`
- **Applicability:** `[Why it could address the scenario symptoms]`
- **Advantages:** `[Key benefits under specific conditions]`
- **Disadvantages & Failure Modes:** `[Why it may degrade performance or fail under high load]`

### Alternative 2: `[Name of Mechanism 2 — e.g., Round Robin (RR) Scheduling / Semaphore / Best Fit]`
- **Operational Principle:** `[How the mechanism functions within the kernel]`
- **Applicability:** `[Why it could address the scenario symptoms]`
- **Advantages:** `[Key benefits under specific conditions]`
- **Disadvantages & Failure Modes:** `[Why it may degrade performance or fail under high load]`

*(Optional) Alternative 3:* `[Name of Mechanism 3 — e.g., Multi-Level Feedback Queue (MLFQ) / Reader-Writer Lock]`
- `[Brief comparative summary]`

---

## F. Comparative Analysis

> **Official Instruction:** Critically evaluate the alternatives against measurable performance criteria appropriate to the OS domain (e.g., response time, turnaround time, throughput, fairness, context-switch frequency, lock contention, fragmentation, head movement). Support the comparison with calculations, traces, or documented principles.

| Evaluation Metric | Alternative 1: `[Name]` | Alternative 2: `[Name]` | Quantitative / Theoretical Basis |
|---|---|---|---|
| **Primary Metric (e.g., Response Time)** | `[Value / Rating]` | `[Value / Rating]` | `[Mathematical calculation / trace proof]` |
| **Throughput / Utilization** | `[Value / Rating]` | `[Value / Rating]` | `[Resource efficiency comparison]` |
| **Fairness / Starvation Risk** | `[Value / Rating]` | `[Value / Rating]` | `[Behavior under skewed burst distributions]` |
| **Overhead (e.g., Context Switching)** | `[Value / Rating]` | `[Value / Rating]` | `[Kernel overhead penalty]` |
| **Implementation Complexity** | `[Value / Rating]` | `[Value / Rating]` | `[Data structure and synchronization cost]` |

*Detailed Analytical Comparison:*  
`[Provide step-by-step calculations, traces, or evidence substantiating the table entries above.]`

---

## G. Selected Solution

> **Official Instruction:** State the explicit, unambiguous engineering decision. Name the selected mechanism and specify all relevant configuration parameters.

- **Selected Mechanism:** `[State exact mechanism chosen — e.g., Preemptive Round Robin Scheduling with Multi-Level Feedback]`
- **Operating Parameters:** `[Specify values — e.g., Time Quantum = 20 ms; Aging interval = 100 ms]`
- **Target Subsystem:** `[Subsystem where the mechanism is deployed]`
- **Primary Selection Criteria:** `[Key performance metric that prioritized this choice over alternatives]`

---

## H. Engineering Justification

> **Official Instruction:** Defend why the selected solution best satisfies the constraints and performance goals. Explain why the rejected alternatives are inferior in this specific operational context.

`[Provide 2–3 structured paragraphs explaining:`  
`1. Why the selected mechanism directly resolves the identified bottleneck.`  
`2. Why the rejected alternatives fail under the given workload constraints.`  
`3. How the empirical/calculated evidence in Section F proves this decision is technically defensible.]`

---

## I. Trade-offs and Limitations

> **Official Instruction:** Transparently discuss what is sacrificed by adopting the chosen mechanism. Identify remaining limitations, potential edge cases, and conditions under which this decision would need to be reversed.

### 1. Identified Trade-offs
- `[Trade-off 1: e.g., Improved response time is achieved at the expense of higher context-switch CPU overhead]`
- `[Trade-off 2: e.g., Strict fairness slightly degrades overall batch throughput]`

### 2. Operational Limitations & Edge Cases
- `[Limitation 1: e.g., If the process queue becomes exceptionally large, scheduling latency increases]`
- `[Edge Case: e.g., Behavior during bursty I/O interruptions]`

### 3. Conditions for Reconsidering the Decision
- `[State explicitly: "If the workload shifts from interactive requests to predominantly long CPU-bound batch jobs, this mechanism should be replaced with SJF or a non-preemptive scheduler to eliminate switching overhead."]`

---

## J. AI Corroboration

> **Official Instruction:** In accordance with Section 14 of the CA1 specification, disclose all use of Generative AI tools. Document the prompts, suggestions received, independent verification methods, and critical reflections on AI correctness.

| Disclosure Field | Student Documentation |
|---|---|
| **AI Tool Used** | `[e.g., Google Gemini / ChatGPT / Claude — specify model/version]` |
| **Purpose of Inquiry** | `[e.g., Brainstorming alternative scheduling policies for interactive workloads]` |
| **AI Suggestion Received** | `[Summarize the key claim or mechanism suggested by the AI]` |
| **Independent Verification Method** | `[Explain how you verified the claim using OS textbooks, manual calculations, or Linux documentation]` |
| **Critical Reflection & Assessment** | `[Mark as: Correct / Partially Correct / Incorrect / Incomplete]`<br>`[Detail any hallucinations, unsafe suggestions, or missing constraints identified in the AI output]` |

---

## K. Final Engineering Decision

> **Official Instruction:** Conclude with a rigorous, professional engineering synthesis in 3 to 5 technically meaningful sentences. Summarize the problem, the chosen intervention, the primary justification, and the primary operational trade-off.

`[Sentence 1: Restate the primary OS failure and root cause in the system context.]`  
`[Sentence 2: Declare the selected OS mechanism and its critical operating parameters.]`  
`[Sentence 3: Summarize the principal performance advantage substantiated by evidence.]`  
`[Sentence 4: Acknowledge the primary engineering trade-off accepted by this choice.]`  
`[Sentence 5: Conclude with the operational boundary condition under which the decision holds.]`

---

## Appendix 1: Student Submission Checklist (CA-1 Section 23)

Before submitting, verify that every item is satisfied:

- [ ] I identified the actual OS problem and subsystem.
- [ ] I explained the relevant OS concept with contextual reasoning.
- [ ] I created an appropriate system model (diagram, table, trace, or math representation).
- [ ] I identified system constraints, workload properties, and explicit assumptions.
- [ ] I analyzed at least two distinct, plausible alternatives.
- [ ] I used appropriate quantitative performance measures.
- [ ] I selected one specific mechanism with operating parameters.
- [ ] I justified my decision using calculations, traces, or technical evidence.
- [ ] I thoroughly discussed trade-offs and operational limitations.
- [ ] I defined the exact condition that would change or reverse my decision.
- [ ] I fully completed the AI Corroboration table with prompt, verification, and critique.
- [ ] I independently verified all AI-generated claims against reliable OS sources.
- [ ] My final conclusion is a technically defensible 3–5 sentence engineering statement.

---

## Appendix 2: Official Marking Rubric Mapping (CA-1 Section 17)

| Criterion | 0 Marks | 1 Mark | 2 Marks | Target Score |
|---|---|---|---|:---:|
| **1. OS Concept Identification** | Concept not identified or incorrect | Correct concept identified but weak explanation | Correct concept identified with clear contextual reasoning | /2 |
| **2. Problem Modelling** | No model or incorrect model | Partially appropriate model with gaps | Appropriate, clear, and well-annotated technical model | /2 |
| **3. Alternative Analysis** | No meaningful alternatives presented | Alternatives listed with superficial comparison | At least two alternatives critically compared using quantitative criteria | /2 |
| **4. Mechanism Selection** | Inappropriate or unstated decision | Reasonable decision but unsupported by constraints | Appropriate decision directly supported by constraints and evidence | /2 |
| **5. Justification & Communication** | Unsupported or vague conclusion | Basic justification with limited evidence | Rigorous, evidence-based engineering justification with trade-offs | /2 |
| **TOTAL** | | | | **/10** |

