# CA-6 Mini Rust OS — Architectural Specification & Viva Guide

## 1. System Overview
**CA-6 Mini Rust OS** is a bare-metal, educational x86_64 operating system written in Rust and assembly. It boots directly from a standard ISO on real hardware or virtual machines (specifically tuned for Oracle VirtualBox) without relying on Linux, Windows, or an underlying OS runtime.

---

## 2. Boot Flow & CPU Mode Transition
```
+-------------------------------------------------------+
| BIOS / UEFI Emulation (VirtualBox)                    |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| GNU GRUB Bootloader (reads ISO, parses ELF binary)    |
| Transfers control to `_start` in 32-bit Protected Mode|
| Checks Multiboot 1 Magic (0x2BADB002 in EAX)          |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| arch/x86_64/boot.asm                                  |
| 1. Checks CPUID & Long Mode (LM) capability           |
| 2. Identity-maps 0..4GB using 4-level Paging          |
|    - PML4 -> PDPT (4 entries) -> 4 Page Directories   |
|    - Maps 2048 x 2MB Huge Pages (0x83)                |
| 3. Loads CR3 with PML4 base physical address          |
| 4. Enables PAE in CR4 (bit 5)                         |
| 5. Sets IA32_EFER.LME (MSR 0xC0000080, bit 8)        |
| 6. Enables Paging (CR0.PG, bit 31)                    |
| 7. Loads 64-bit GDT (`gdt64`)                         |
| 8. Far jump `jmp 0x08:long_mode_start`                |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
| 64-bit Long Mode Entry (`long_mode_start`)            |
| 1. Loads data segment registers (DS, ES, FS, GS, SS)  |
| 2. Sets RSP to 64KB kernel stack                      |
| 3. Calls Rust Entry Point: `rust_main()`              |
+-------------------------------------------------------+
```

---

## 3. Kernel Subsystems

### 3.1. Display & Serial Console Drivers
- **VGA Text Mode Buffer**: Memory-mapped at physical address `0xB8000`. 80 columns by 25 rows. Writes characters paired with 8-bit attribute bytes (foreground/background color). Includes auto-scrolling and row-clearing logic.
- **UART 16550 Serial Driver**: Mapped to I/O port `0x3F8` (COM1). Configured to 38400 baud, 8 data bits, no parity, 1 stop bit, FIFO enabled. All VGA writes are mirrored to the serial port, enabling simultaneous graphical terminal output and host log capturing.

### 3.2. Synchronization: SpinLock Primitive
- Implemented in `src/sync/spinlock.rs` using `core::sync::atomic::AtomicBool`.
- Acquire loop utilizes `compare_exchange_weak` with `Acquire` memory ordering and `core::hint::spin_loop()` CPU pipeline relaxation.
- Release utilizes `store(false, Ordering::Release)` encapsulated within an RAII `Drop` implementation (`SpinLockGuard`).

### 3.3. Memory Management: Kernel Heap Allocator
- Implemented in `src/memory/allocator.rs`.
- Fixed-size 64KB kernel heap with linked block tracking.
- Every block is prefixed with a `BlockHeader` containing:
  - Magic sanity marker (`0xCA60CA60`)
  - Payload size
  - Allocation state (`is_free: bool`)
  - Pointer to next block
- Supports block splitting during allocation and adjacent block coalescing during deallocation.
- Prevents double-free and memory corruption via sanity assertions.

### 3.4. Hardware Timer: 8254 PIT & TSC
- Implemented in `src/timer/pit.rs`.
- Programs Intel 8254 Programmable Interval Timer (PIT) at I/O ports `0x40` (Channel 0) and `0x43` (Command Register) to 100 Hz.
- Reads hardware Time Stamp Counter via `rdtsc` instruction.

### 3.5. Task Management & Round Robin Scheduler
- Implemented in `src/task/task.rs` and `src/scheduler/rr.rs`.
- **Task Structure**:
  - `id`: Unique identifier
  - `name`: Human-readable task name
  - `state`: State machine (`READY`, `RUNNING`, `BLOCKED`, `TERMINATED`)
  - `priority`: Scheduling priority
  - `total_runtime_ticks`: Cumulative ticks spent in execution
  - `remaining_quantum`: Active time slice
  - `total_iterations` & `iterations_completed`: Progress metrics
  - `action`: Workload routine callback
- **Round Robin Algorithm**:
  - Configurable quantum (default: 2 ticks).
  - Circular traversal of the Ready Queue.
  - When a task runs for its quantum, the scheduler logs the quantum expiration and context switch, preempting the task back to `READY` and dispatching the next `READY` task.
  - Upon completing its workload, a task transitions to `TERMINATED`.

### 3.6. PCI Configuration Space & Device Enumeration
- Implemented in `src/drivers/pci.rs`.
- Uses PCI Configuration Mechanism #1 (`0x0CF8` Address, `0x0CFC` Data).
- Scans buses 0..7, devices 0..31, functions 0..7.
- Discovers Intel PRO/1000 MT Desktop (`8086:100E`).
- Reads BAR0 (`offset 0x10`) to extract MMIO base address (`0xF0000000`).
- Enables PCI Bus Mastering, Memory Space, and I/O Space via Command Register (`offset 0x04`).

### 3.7. Intel 82540EM (e1000) Network Driver
- Implemented in `src/drivers/e1000.rs`.
- Direct Memory-Mapped I/O register control (`REG_CTRL`, `REG_STATUS`, `REG_RCTL`, `REG_TCTL`, `REG_RAL0`/`REG_RAH0`).
- Extracts authentic hardware MAC from `RAL0`/`RAH0` (`08:00:27:38:ad:8d`).
- Detects physical link status and negotiation speed (1000 Mbps).
- Circular DMA Descriptor Rings:
  - 32 Receive descriptors (`RxDesc`) pointing to pre-allocated 2KB buffers.
  - 16 Transmit descriptors (`TxDesc`).
  - High-performance, interrupt-free polled packet transmission and reception.

### 3.8. Bare-Metal Network Stack (DHCP, ARP, IPv4, ICMP)
- Implemented in `src/net/stack.rs`.
- **DHCP**: Broadcasts DHCP Discover over UDP (Port 68 -> 67). Receives DHCP Offer/Ack from VirtualBox NAT gateway (`10.0.2.2`), leasing IP (`10.0.2.15`), Subnet Mask (`255.255.255.0`), and DNS.
- **ARP**: Responds to ARP requests from gateway for address resolution.
- **ICMP**: Dispatches ICMP Echo Request (Type 8) to gateway (`10.0.2.2`), parses incoming Echo Reply (Type 0), and computes round-trip latency in CPU cycles.

### 3.9. Interactive PS/2 Console Shell
- Implemented in `src/drivers/keyboard.rs` and `src/kernel/shell.rs`.
- Reads hardware PS/2 controller data at port `0x60` and status at `0x64`.
- Converts Scancode Set 1 into ASCII characters with backspace and line buffering.
- Supports interactive diagnostic commands: `help`, `pci`, `net`, `ip`, `ping`, `ticks`, `scheduler`, `clear`, `reboot`.

---

## 4. Key Viva Questions & Answers

1. **Why does the bootloader start in 32-bit mode instead of 64-bit mode?**
   - *Answer:* The standard Multiboot specification (used by GRUB) guarantees the CPU enters the kernel in 32-bit Protected Mode with paging disabled. Operating systems wishing to run in 64-bit Long Mode must manually construct page tables (PML4), enable PAE, set the Long Mode Enable (LME) bit in EFER MSR, enable paging in CR0, and execute a far jump to a 64-bit code segment descriptor.

2. **Why was identity paging expanded to 4 GB?**
   - *Answer:* PCI Memory-Mapped I/O (MMIO) registers (like BAR0 for the Intel e1000 adapter) are assigned by VirtualBox firmware above the main RAM boundary, typically at `0xF0000000` (3.75 GB). A kernel mapping only 1 GB would trigger a fatal Page Fault when reading BAR0. Expanding paging to 4 GB (2,048 entries of 2MB pages) provides seamless identity mapping across all physical 32-bit MMIO devices.

3. **How does the e1000 driver transmit packets without interrupts?**
   - *Answer:* The e1000 driver configures a circular ring of Transmit Descriptors (`TxDesc`). To transmit, it writes packet bytes into an aligned buffer, points the current descriptor's `addr` to this buffer, sets command bits `EOP | IFCS | RS`, and increments the hardware Tail pointer (`TDT`). It then polls the `status` byte until the `DD` (Descriptor Done) bit is asserted by the NIC.

4. **How does VirtualBox NAT handle DHCP and ICMP?**
   - *Answer:* VirtualBox NAT acts as an internal router and DHCP server at IP `10.0.2.2`. When our kernel broadcasts a DHCP Discover packet, VirtualBox intercepts it and assigns `10.0.2.15`. When an ICMP Echo Request is transmitted to `10.0.2.2`, VirtualBox NAT generates an ICMP Echo Reply, confirming full bidirectional frame exchange.
