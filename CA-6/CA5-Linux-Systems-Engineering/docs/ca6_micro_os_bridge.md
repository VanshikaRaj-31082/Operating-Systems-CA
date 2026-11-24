# CA5 to CA6 Technical Bridge: Systems Engineering to Rust Micro-OS
## Architectural Mapping from Linux Concurrency to Micro-OS Kernel Construction

**Project:** `CA5-Linux-Systems-Engineering`  
**Author:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University)  
**Academic Year:** 2026–2027  

---

### 1. Conceptual Position in Assessment Progression

The OS assessment journey transitions from theoretical models to low-level implementation:
```
CA1 (Think) -> CA2 (Measure) -> CA3 (Debug) -> CA4 (Research) -> CA5 (Engineer Linux) -> CA6 (Build Micro-OS) -> CA7 (Defend)
```
While **CA4** investigated deadlock algorithms through simulation and **CA5** investigated real Linux process concurrency and `/proc` instrumentation, **CA6** requires building a bare-metal or user-space **Rust Micro-OS**.

This document outlines the direct technical bridge between the Linux mechanisms observed in CA5 and their corresponding kernel implementations in CA6.

---

### 2. Comprehensive Mechanism Mapping Table

| Real Linux Mechanism (Observed in CA5) | Kernel Mechanism in CA6 (Rust Micro-OS) | Implementation Difference & Architectural Insight |
| :--- | :--- | :--- |
| **Process (`task_struct`, `/proc/<pid>`)** | **`TaskControlBlock` (TCB)** | In Linux, processes have virtual address spaces (`mm_struct`) and file tables (`files_struct`). In a minimal Rust Micro-OS, a task is represented as a TCB containing saved CPU registers (`rsp`, `rip`, `rflags`), a unique Task ID, task state (`Ready`, `Running`, `Blocked`), and a private stack pointer. |
| **Thread (`/proc/<pid>/task/<tid>`)** | **Kernel Execution Context** | In Linux, threads are light-weight processes sharing the thread group ID (`tgid`). In CA6, kernel execution contexts are co-operative or preemptible execution stacks scheduled on the bare-metal CPU. |
| **Linux CFS Scheduler & `nice` Priority** | **Priority / Round-Robin Scheduler** | Linux CFS uses red-black trees tracking virtual runtime (`vruntime`). In CA6, a simplified scheduler maintains a ready queue (array/linked list) and context-switches tasks during periodic timer interrupts. |
| **Context Switch (`voluntary_ctxt_switches`)** | **Hardware Register Save/Restore** | In CA5, context switches were observed as numbers in `/proc/<pid>/status`. In CA6, context switching is implemented directly in assembly/Rust by pushing registers to the current stack, swapping stack pointers (`mov rsp, next_task_rsp`), and popping the next task's registers. |
| **POSIX Mutex / Futex System Call** | **Kernel Spinlock / Sleep Lock** | Linux futexes sleep in user space if uncontended and invoke `sys_futex` to sleep on a kernel wait queue if contended. In CA6, interrupt-disabled spinlocks (`AtomicBool` with CAS) are used inside the kernel; sleep locks place the calling task onto a waiting queue and call `schedule()`. |
| **POSIX `sched_yield` (`time.sleep(0)`)** | **`sys_yield()` System Call** | In CA5, `sched_yield` triggered thread preemption. In CA6, `sys_yield` transitions the current task to `Ready`, pushes it to the back of the run queue, and invokes the scheduler. |
| **Wait Channel (`/proc/<pid>/task/<tid>/wchan`)** | **Task Block Reason / Wait Queue** | Linux exposes the kernel sleep function via `wchan`. In CA6, the TCB carries a `blocked_on` field pointing to a synchronization channel or timer descriptor. |
| **Memory Info (`/proc/meminfo`, `VmRSS`)** | **Physical Frame Allocator & Heap** | Linux manages virtual memory via multi-level page tables and page cache. In CA6, a bitmap or buddy allocator manages physical frames (4 KiB pages), and a bump or linked-list allocator manages kernel heap memory. |

---

### 3. Concrete Rust Demonstration (`rust_bridge/src/main.rs`)

To concretely demonstrate this bridge, a Rust module was constructed in `rust_bridge/src/main.rs`:

```rust
pub struct SpinLock {
    locked: AtomicBool,
}

impl SpinLock {
    pub const fn new() -> Self {
        Self { locked: AtomicBool::new(false) }
    }

    pub fn lock(&self) {
        while self.locked.compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed).is_err() {
            std::hint::spin_loop();
        }
    }

    pub fn unlock(&self) {
        self.locked.store(false, Ordering::Release);
    }
}
```

#### Key Architectural Takeaways for CA6:
1. **Lock-Free Atomics:** Direct hardware read-modify-write instructions (such as `LOCK XADD` on x86_64) provide zero-overhead atomic synchronization without kernel intervention.
2. **Spinlocks for Kernel Interrupts:** In kernel space, interrupt service routines (ISRs) cannot sleep because they execute outside task context. Therefore, spinlocks with local interrupts disabled are mandatory for protecting kernel scheduler data structures.
3. **Sleeping Locks for Long Critical Sections:** Spinlocks waste CPU cycles when held across long operations. Tasks must be placed into a `Blocked` state on a wait queue, yielding the CPU to other runnable tasks—mirroring the voluntary context switches observed in CA5.
