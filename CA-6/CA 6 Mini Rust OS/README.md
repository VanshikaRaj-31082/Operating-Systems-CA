# CA-6 Mini Rust OS — Bare-Metal x86_64 Educational Operating System

A bare-metal x86_64 microkernel written in Rust and assembly for the Operating Systems CA-6 course project. Features a preemptive/quantum Round Robin scheduler, 64KB heap allocator, atomic synchronization primitives, PCI enumeration, a custom polled Intel 82540EM Gigabit Ethernet driver, full DHCP dynamic IP leasing, bidirectional ICMP ping, and an interactive PS/2 console shell in Oracle VirtualBox.

---

## 1. Quick Start Guide for Professor / Evaluation

### Target Environment & Prerequisites
- **Host**: Windows 10/11 with Oracle VirtualBox 7.x
- **Build Environment**: WSL 2 (Ubuntu) with standard Rust toolchain (`x86_64-unknown-none`), NASM, GRUB (`grub-mkrescue`), and xorriso.

---

### Step 1: VirtualBox VM Configuration

Ensure the VirtualBox VM has the following settings:
1. **System**:
   - **Base Memory**: 256 MB or 512 MB
   - **Boot Order**: Optical first
   - **Chipset**: PIIX3 (Default)
   - **Extended Features**: Enable I/O APIC (Optional), EFI disabled (BIOS boot mode)
2. **Storage**:
   - Controller: IDE (or SATA)
   - Optical Drive: Choose `output/os.iso`
3. **Network (Crucial for Networking Demonstration)**:
   - **Enable Network Adapter**: Checked
   - **Attached to**: `NAT`
   - **Adapter Type**: `Intel PRO/1000 MT Desktop (82540EM)`
   - **Cable Connected**: Checked
4. **Serial Ports (Optional, for Live Host Terminal Logging)**:
   - Port 1: Checked, COM1 (`0x3F8`, IRQ 4), Mode: Raw File, Path: `results/virtualbox_serial.log`

---

### Step 2: One-Click Launch in VirtualBox

**From Windows PowerShell:**
```powershell
# Power on and launch the VM
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm "CA-6 Mini Rust OS"
```

**Or Launch the VirtualBox GUI:**
Open Oracle VirtualBox, select **CA-6 Mini Rust OS**, and click **Start**.

---

### Step 3: Rebuilding the ISO (WSL Ubuntu)

To build from scratch in WSL Ubuntu:
```bash
cd "/mnt/c/Users/Vanshika/Downloads/CA 6 Mini Rust OS"
chmod +x scripts/*.sh
./scripts/build.sh
```
This produces `output/os.iso` verified by `grub-file --is-x86-multiboot`.

---

## 2. Verified Subsystems & Live VirtualBox Test Results

| Subsystem | Status | Verification Detail |
| :--- | :---: | :--- |
| **Boot & CPU Mode** | **VERIFIED** | Multiboot 1 entry (`0x1BADB002`), Long Mode transition, 4GB 4-level identity paging (`PML4` -> `PDPT` -> `PD`). |
| **VGA Display** | **VERIFIED** | 80x25 text mode buffer (`0xB8000`) with color styling, scrolling, and dual UART COM1 (`0x3F8`) serial mirroring. |
| **SpinLock Primitive** | **VERIFIED** | `AtomicBool` with `compare_exchange_weak`, `Acquire`/`Release` barriers, RAII guard drop unlock, and `try_lock()`. |
| **Kernel Allocator** | **VERIFIED** | 64KB heap, `0xCA60CA60` canary blocks, 16-byte alignment, non-overlapping allocations, block reuse on free. |
| **Hardware PIT & TSC** | **VERIFIED** | 8254 Timer Channel 0 set to 100 Hz (`0x40`/`0x43`), hardware RDTSC cycle measurement. |
| **Round Robin Scheduler** | **VERIFIED** | Configurable quantum (2 ticks), circular queue traversal across 4 distinct tasks, context switch state logging. |
| **PCI Scanning** | **VERIFIED** | Scanned buses 0..7, enumerated Intel 82540EM (`8086:100E`) at `00:03.0`, mapped BAR0 MMIO at `0xF0000000`. |
| **Intel e1000 Driver** | **VERIFIED** | Bus Mastering enabled, MMIO register access, hardware MAC `08:00:27:38:ad:8d` extracted, 1000 Mbps link asserted. |
| **DHCP IP Lease** | **VERIFIED** | Transmitted DHCP Discover over UDP:67, received DHCP Offer/Ack, leased IP `10.0.2.15` from gateway `10.0.2.2`. |
| **Bidirectional ICMP Ping**| **VERIFIED** | Dispatched Echo Request via e1000 TX ring, received Echo Reply from gateway `10.0.2.2` (RTT ~32M cycles). |
| **Interactive Console** | **VERIFIED** | Polled PS/2 keyboard driver (`0x60`/`0x64`) with command interpreter (`help`, `pci`, `net`, `ip`, `ping`, `ticks`, `scheduler`). |

---

## 3. Interactive Console Commands

Once booted into VirtualBox, the system launches an interactive shell (`ca6-os> `). You can type:

- `help` — Show command reference
- `pci` — Run live PCI bus scan and list network devices
- `net` — Display complete Intel e1000 driver and link diagnostics
- `net status` — Check physical/emulated Ethernet link connectivity
- `net mac` — Display real hardware MAC address (`08:00:27:38:ad:8d`)
- `net dhcp` — Trigger manual DHCP lease renewal from VirtualBox NAT router
- `ip` — Print current IPv4 network parameters (IP, Subnet, Gateway, DNS)
- `ping` — Transmit ICMP Echo Request to VirtualBox NAT router (`10.0.2.2`) and wait for reply
- `ticks` or `uptime` — Display current CPU cycle count via hardware RDTSC
- `scheduler` — Re-run the Round Robin task execution demonstration
- `clear` — Clear the VGA screen
- `reboot` — Hardware reset via keyboard controller

---

## 4. Key Architectural Highlights for Viva

1. **How is BAR0 MMIO accessed in 64-bit mode without page faults?**
   - In `arch/x86_64/boot.asm`, the identity-mapping paging structures were expanded from 1 GB to **4 GB** by populating 4 Page Directory tables with 2,048 entries of 2MB huge pages (`0x83`). This allows direct virtual-to-physical mapping of high 32-bit MMIO regions (such as `0xF0000000`) assigned by VirtualBox.

2. **How does packet transmission and reception work without interrupts?**
   - The driver implements the official Intel e1000 descriptor ring architecture:
     - 32 Receive descriptors (`RxDesc`) pointing to pre-allocated 2KB DMA buffers.
     - 16 Transmit descriptors (`TxDesc`).
     - Safe, high-performance polling inspects the `status` byte (Descriptor Done bit 0) and advances the Tail register (`TDT` / `RDT`), avoiding complex IDT/PIC interrupt fragility in bare metal.

3. **How does DHCP work with VirtualBox NAT?**
   - The kernel crafts a raw Ethernet frame containing an IPv4 UDP packet addressed to broadcast `255.255.255.255:67`. VirtualBox NAT intercepts this packet, assigns dynamic IP `10.0.2.15`, and replies with DHCP Offer/Ack over UDP:68. The kernel parses the DHCP options to extract Subnet Mask (`255.255.255.0`), Default Gateway (`10.0.2.2`), and DNS server.

---

## 5. Artifacts & Deliverables
- **Bootable ISO**: `output/os.iso` (5.5 MB)
- **Previous Working ISO Backup**: `output/os.iso.prev` (5.5 MB)
- **Kernel Binary**: `build/kernel.bin` (154 KB)
- **Genuine Execution Log**: `results/virtualbox_serial.log`
- **Automated Test Report**: `results/test_report.md` (13/13 tests passed)
- **Screenshots**: `screenshots/virtualbox_final_net.png`, `screenshots/virtualbox_verified_networking.png`
