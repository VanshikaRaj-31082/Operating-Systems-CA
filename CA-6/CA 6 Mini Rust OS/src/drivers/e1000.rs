#![allow(dead_code)]
use core::ptr::{read_volatile, write_volatile, addr_of_mut};
use crate::drivers::pci::{self, NicInfo};
use crate::sync::SpinLock;

// Intel 82540EM Registers
const REG_CTRL: usize    = 0x0000;
const REG_STATUS: usize  = 0x0008;
const REG_EEC: usize     = 0x0010;
const REG_EERD: usize    = 0x0014;
const REG_ICR: usize     = 0x00C0;
const REG_IMS: usize     = 0x00D0;
const REG_IMC: usize     = 0x00D8;
const REG_RCTL: usize    = 0x0100;
const REG_TCTL: usize    = 0x0400;
const REG_TIPG: usize    = 0x0410;
const REG_RDBAL: usize   = 0x2800;
const REG_RDBAH: usize   = 0x2804;
const REG_RDLEN: usize   = 0x2808;
const REG_RDH: usize     = 0x2810;
const REG_RDT: usize     = 0x2818;
const REG_TDBAL: usize   = 0x3800;
const REG_TDBAH: usize   = 0x3804;
const REG_TDLEN: usize   = 0x3808;
const REG_TDH: usize     = 0x3810;
const REG_TDT: usize     = 0x3818;
const REG_MTA: usize     = 0x5200;
const REG_RAL0: usize    = 0x5400;
const REG_RAH0: usize    = 0x5404;

// Control Register Bits
const CTRL_SLU: u32 = 1 << 6;   // Set Link Up
const CTRL_RST: u32 = 1 << 26;  // Device Reset

// RCTL Bits
const RCTL_EN: u32   = 1 << 1;   // Receiver Enable
const RCTL_SBP: u32  = 1 << 2;   // Store Bad Packets
const RCTL_UPE: u32  = 1 << 3;   // Unicast Promiscuous
const RCTL_MPE: u32  = 1 << 4;   // Multicast Promiscuous
const RCTL_BAM: u32  = 1 << 15;  // Broadcast Accept Mode
const RCTL_BSIZE_2048: u32 = 0 << 16;
const RCTL_SECRC: u32 = 1 << 26; // Strip Ethernet CRC

// TCTL Bits
const TCTL_EN: u32  = 1 << 1;   // Transmit Enable
const TCTL_PSP: u32 = 1 << 3;   // Pad Short Packets
const TCTL_CT_SHIFT: u32 = 4;
const TCTL_COLD_SHIFT: u32 = 12;

// Descriptors
const NUM_RX_DESC: usize = 32;
const NUM_TX_DESC: usize = 16;
const RX_BUFFER_SIZE: usize = 2048;

#[repr(C, align(16))]
#[derive(Clone, Copy)]
pub struct RxDesc {
    pub addr: u64,
    pub length: u16,
    pub checksum: u16,
    pub status: u8,
    pub errors: u8,
    pub special: u16,
}

#[repr(C, align(16))]
#[derive(Clone, Copy)]
pub struct TxDesc {
    pub addr: u64,
    pub length: u16,
    pub cso: u8,
    pub cmd: u8,
    pub status: u8,
    pub css: u8,
    pub special: u16,
}

#[repr(align(16))]
struct RxRing([RxDesc; NUM_RX_DESC]);

#[repr(align(16))]
struct TxRing([TxDesc; NUM_TX_DESC]);

#[repr(align(16))]
struct RxBuffers([[u8; RX_BUFFER_SIZE]; NUM_RX_DESC]);

#[repr(align(16))]
struct TxBuffers([[u8; RX_BUFFER_SIZE]; NUM_TX_DESC]);

static mut RX_RING: RxRing = RxRing([RxDesc {
    addr: 0,
    length: 0,
    checksum: 0,
    status: 0,
    errors: 0,
    special: 0,
}; NUM_RX_DESC]);

static mut TX_RING: TxRing = TxRing([TxDesc {
    addr: 0,
    length: 0,
    cso: 0,
    cmd: 0,
    status: 0,
    css: 0,
    special: 0,
}; NUM_TX_DESC]);

static mut RX_BUFFERS: RxBuffers = RxBuffers([[0; RX_BUFFER_SIZE]; NUM_RX_DESC]);
static mut TX_BUFFERS: TxBuffers = TxBuffers([[0; RX_BUFFER_SIZE]; NUM_TX_DESC]);

pub struct E1000Driver {
    pub mmio_base: usize,
    pub mac: [u8; 6],
    pub rx_cur: usize,
    pub tx_cur: usize,
    pub initialized: bool,
    pub link_up: bool,
    pub link_speed_mbps: u32,
}

unsafe impl Send for E1000Driver {}

impl E1000Driver {
    pub const fn new() -> Self {
        Self {
            mmio_base: 0,
            mac: [0; 6],
            rx_cur: 0,
            tx_cur: 0,
            initialized: false,
            link_up: false,
            link_speed_mbps: 0,
        }
    }

    #[inline]
    fn write_reg(&self, reg: usize, val: u32) {
        unsafe {
            write_volatile((self.mmio_base + reg) as *mut u32, val);
        }
    }

    #[inline]
    fn read_reg(&self, reg: usize) -> u32 {
        unsafe {
            read_volatile((self.mmio_base + reg) as *const u32)
        }
    }

    fn read_eeprom(&self, addr: u8) -> u16 {
        self.write_reg(REG_EERD, 1 | ((addr as u32) << 8));
        let mut timeout = 100_000;
        while timeout > 0 {
            let val = self.read_reg(REG_EERD);
            if (val & (1 << 4)) != 0 {
                return ((val >> 16) & 0xFFFF) as u16;
            }
            timeout -= 1;
            core::hint::spin_loop();
        }
        0
    }

    pub fn init(&mut self, nic: &NicInfo) -> bool {
        // BAR0 points to the 128KB MMIO register bank
        let raw_bar0 = nic.bar0;
        if (raw_bar0 & 1) != 0 {
            crate::println!("[E1000] Error: BAR0 is I/O mapped, expected MMIO!");
            return false;
        }

        self.mmio_base = (raw_bar0 & 0xFFFFFFF0) as usize;
        crate::println!("[E1000] Enabling PCI Bus Mastering & Memory Space...");
        pci::pci_enable_bus_master(nic.bus, nic.device, nic.function);

        crate::println!("[E1000] MMIO base address: {:#010x}", self.mmio_base);

        // Read hardware MAC address from RAL0/RAH0 or EEPROM
        let ral = self.read_reg(REG_RAL0);
        let rah = self.read_reg(REG_RAH0);

        if ral != 0 || (rah & 0xFFFF) != 0 {
            self.mac[0] = (ral & 0xFF) as u8;
            self.mac[1] = ((ral >> 8) & 0xFF) as u8;
            self.mac[2] = ((ral >> 16) & 0xFF) as u8;
            self.mac[3] = ((ral >> 24) & 0xFF) as u8;
            self.mac[4] = (rah & 0xFF) as u8;
            self.mac[5] = ((rah >> 8) & 0xFF) as u8;
        } else {
            // Fallback: Read words 0, 1, 2 from EEPROM
            let w0 = self.read_eeprom(0);
            let w1 = self.read_eeprom(1);
            let w2 = self.read_eeprom(2);
            self.mac[0] = (w0 & 0xFF) as u8;
            self.mac[1] = ((w0 >> 8) & 0xFF) as u8;
            self.mac[2] = (w1 & 0xFF) as u8;
            self.mac[3] = ((w1 >> 8) & 0xFF) as u8;
            self.mac[4] = (w2 & 0xFF) as u8;
            self.mac[5] = ((w2 >> 8) & 0xFF) as u8;
        }

        // Disable all interrupts (we use clean, safe polling)
        self.write_reg(REG_IMC, 0xFFFFFFFF);
        let _ = self.read_reg(REG_ICR); // Read to clear pending

        // Set Link Up (SLU) in Device Control
        let ctrl = self.read_reg(REG_CTRL);
        self.write_reg(REG_CTRL, ctrl | CTRL_SLU);

        // Clear Multicast Table Array (MTA)
        for i in 0..128 {
            self.write_reg(REG_MTA + (i * 4), 0);
        }

        // Initialize RX Ring
        unsafe {
            for i in 0..NUM_RX_DESC {
                let buf_addr = RX_BUFFERS.0[i].as_ptr() as u64;
                RX_RING.0[i].addr = buf_addr;
                RX_RING.0[i].status = 0;
            }

            let rx_ring_base = addr_of_mut!(RX_RING) as u64;
            self.write_reg(REG_RDBAL, (rx_ring_base & 0xFFFFFFFF) as u32);
            self.write_reg(REG_RDBAH, (rx_ring_base >> 32) as u32);
            self.write_reg(REG_RDLEN, (NUM_RX_DESC * core::mem::size_of::<RxDesc>()) as u32);
            self.write_reg(REG_RDH, 0);
            self.write_reg(REG_RDT, (NUM_RX_DESC - 1) as u32);
        }
        self.rx_cur = 0;

        // Initialize TX Ring
        unsafe {
            for i in 0..NUM_TX_DESC {
                TX_RING.0[i].addr = 0;
                TX_RING.0[i].cmd = 0;
                TX_RING.0[i].status = 1; // Mark initially done
            }

            let tx_ring_base = addr_of_mut!(TX_RING) as u64;
            self.write_reg(REG_TDBAL, (tx_ring_base & 0xFFFFFFFF) as u32);
            self.write_reg(REG_TDBAH, (tx_ring_base >> 32) as u32);
            self.write_reg(REG_TDLEN, (NUM_TX_DESC * core::mem::size_of::<TxDesc>()) as u32);
            self.write_reg(REG_TDH, 0);
            self.write_reg(REG_TDT, 0);
        }
        self.tx_cur = 0;

        // Enable Receiver
        self.write_reg(
            REG_RCTL,
            RCTL_EN | RCTL_BAM | RCTL_BSIZE_2048 | RCTL_SECRC | RCTL_UPE | RCTL_MPE,
        );

        // Configure Transmit Inter-Packet Gap (TIPG)
        self.write_reg(REG_TIPG, 10 | (10 << 10) | (10 << 20));

        // Enable Transmitter
        self.write_reg(
            REG_TCTL,
            TCTL_EN | TCTL_PSP | (15 << TCTL_CT_SHIFT) | (64 << TCTL_COLD_SHIFT),
        );

        // Wait briefly for hardware auto-negotiation link up
        for _ in 0..100_000 {
            if self.update_link_status() {
                break;
            }
            core::hint::spin_loop();
        }
        self.initialized = true;
        true
    }

    pub fn update_link_status(&mut self) -> bool {
        let status = self.read_reg(REG_STATUS);
        self.link_up = (status & 2) != 0;
        self.link_speed_mbps = match (status >> 6) & 3 {
            0 => 10,
            1 => 100,
            2 | 3 => 1000,
            _ => 0,
        };
        self.link_up
    }

    pub fn send_packet(&mut self, packet: &[u8]) -> bool {
        if !self.initialized || packet.is_empty() || packet.len() > RX_BUFFER_SIZE {
            return false;
        }

        let cur = self.tx_cur;
        unsafe {
            // Check if descriptor is available (status & 1 == DD)
            if (TX_RING.0[cur].status & 1) == 0 {
                return false; // TX ring full
            }

            // Copy data into static TX buffer
            let tx_buf = &mut TX_BUFFERS.0[cur];
            tx_buf[..packet.len()].copy_from_slice(packet);

            TX_RING.0[cur].addr = tx_buf.as_ptr() as u64;
            TX_RING.0[cur].length = packet.len() as u16;
            // CMD: Bit 0 = EOP (End of Packet), Bit 1 = IFCS (Insert FCS/CRC), Bit 3 = RS (Report Status)
            TX_RING.0[cur].cmd = (1 << 0) | (1 << 1) | (1 << 3);
            TX_RING.0[cur].status = 0;

            // Increment Tail pointer to tell NIC to transmit
            self.tx_cur = (cur + 1) % NUM_TX_DESC;
            self.write_reg(REG_TDT, self.tx_cur as u32);
        }

        // Wait with spin loop for transmission completion (polled mode)
        let mut timeout = 200_000;
        while timeout > 0 {
            unsafe {
                if (TX_RING.0[cur].status & 1) != 0 {
                    return true;
                }
            }
            timeout -= 1;
            core::hint::spin_loop();
        }
        false
    }

    pub fn receive_packet(&mut self, buf: &mut [u8]) -> Option<usize> {
        if !self.initialized {
            return None;
        }

        let cur = self.rx_cur;
        unsafe {
            let status = RX_RING.0[cur].status;
            // Bit 0 = DD (Descriptor Done)
            if (status & 1) == 0 {
                return None; // No packet available
            }

            let len = RX_RING.0[cur].length as usize;
            if len > 0 && len <= buf.len() {
                buf[..len].copy_from_slice(&RX_BUFFERS.0[cur][..len]);
            }

            // Reset descriptor status and advance tail
            RX_RING.0[cur].status = 0;
            self.rx_cur = (cur + 1) % NUM_RX_DESC;
            self.write_reg(REG_RDT, cur as u32);

            Some(len)
        }
    }
}

pub static E1000: SpinLock<E1000Driver> = SpinLock::new(E1000Driver::new());
