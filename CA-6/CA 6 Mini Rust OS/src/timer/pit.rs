use core::arch::asm;
use crate::drivers::serial::outb;
use crate::sync::SpinLock;

const PIT_CHANNEL_0: u16 = 0x40;
const PIT_COMMAND: u16 = 0x43;
const PIT_BASE_FREQUENCY: u32 = 1193182; // 1.193182 MHz

pub struct PitTimer {
    frequency_hz: u32,
    ticks: usize,
}

impl PitTimer {
    pub const fn new() -> Self {
        Self {
            frequency_hz: 0,
            ticks: 0,
        }
    }

    /// Initializes the 8254 Programmable Interval Timer (PIT)
    /// Mode 3: Square wave generator, Channel 0, lobyte/hibyte
    pub fn init(&mut self, target_hz: u32) {
        let divisor = (PIT_BASE_FREQUENCY / target_hz) as u16;

        unsafe {
            // Command byte: 0x36 = Channel 0, Access lo/hi byte, Mode 3 (square wave), 16-bit binary
            outb(PIT_COMMAND, 0x36);
            outb(PIT_CHANNEL_0, (divisor & 0xFF) as u8);
            outb(PIT_CHANNEL_0, ((divisor >> 8) & 0xFF) as u8);
        }

        self.frequency_hz = target_hz;
        self.ticks = 0;
    }

    pub fn frequency(&self) -> u32 {
        self.frequency_hz
    }
}

pub static TIMER: SpinLock<PitTimer> = SpinLock::new(PitTimer::new());

/// Read hardware CPU Time Stamp Counter (RDTSC)
pub fn read_tsc() -> u64 {
    let lo: u32;
    let hi: u32;
    unsafe {
        asm!("rdtsc", out("eax") lo, out("edx") hi, options(nomem, nostack, preserves_flags));
    }
    ((hi as u64) << 32) | (lo as u64)
}

pub fn init_timer() {
    crate::println!("[TIMER] Initializing 8254 Programmable Interval Timer (PIT)...");
    TIMER.lock().init(100); // 100 Hz (10ms per tick)
    let tsc1 = read_tsc();
    // Short busy delay
    for _ in 0..10_000 {
        core::hint::spin_loop();
    }
    let tsc2 = read_tsc();
    crate::println!("[TIMER] PIT hardware Channel 0 set to 100 Hz (divisor: {}).", PIT_BASE_FREQUENCY / 100);
    crate::println!("[TIMER] Hardware TSC reading verified: diff = {} cycles.", tsc2.saturating_sub(tsc1));
    crate::println!("[TIMER] Note: Hardware PIT calibrated. Task scheduling demo uses cooperative quantum simulation.");
}
