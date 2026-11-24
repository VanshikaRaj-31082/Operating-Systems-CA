use core::arch::asm;
use core::fmt;
use crate::sync::SpinLock;

const COM1: u16 = 0x3F8;

#[inline]
pub unsafe fn outb(port: u16, val: u8) {
    asm!("out dx, al", in("dx") port, in("al") val, options(nomem, nostack, preserves_flags));
}

#[inline]
pub unsafe fn inb(port: u16) -> u8 {
    let res: u8;
    asm!("in al, dx", in("dx") port, out("al") res, options(nomem, nostack, preserves_flags));
    res
}

pub struct SerialPort {
    port: u16,
    initialized: bool,
}

impl SerialPort {
    pub const fn new(port: u16) -> Self {
        Self {
            port,
            initialized: false,
        }
    }

    pub fn init(&mut self) {
        unsafe {
            outb(self.port + 1, 0x00); // Disable all interrupts
            outb(self.port + 3, 0x80); // Enable DLAB (set baud rate divisor)
            outb(self.port + 0, 0x03); // Set divisor to 3 (lo byte) 38400 baud
            outb(self.port + 1, 0x00); //                  (hi byte)
            outb(self.port + 3, 0x03); // 8 bits, no parity, one stop bit
            outb(self.port + 2, 0xC7); // Enable FIFO, clear them, with 14-byte threshold
            outb(self.port + 4, 0x0B); // IRQs enabled, RTS/DSR set
        }
        self.initialized = true;
    }

    fn is_transmit_empty(&self) -> bool {
        unsafe { (inb(self.port + 5) & 0x20) != 0 }
    }

    pub fn write_byte(&mut self, byte: u8) {
        if !self.initialized {
            self.init();
        }
        while !self.is_transmit_empty() {
            core::hint::spin_loop();
        }
        unsafe {
            outb(self.port, byte);
        }
    }

    pub fn write_string(&mut self, s: &str) {
        for byte in s.bytes() {
            if byte == b'\n' {
                self.write_byte(b'\r');
            }
            self.write_byte(byte);
        }
    }
}

impl fmt::Write for SerialPort {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        self.write_string(s);
        Ok(())
    }
}

pub static SERIAL1: SpinLock<SerialPort> = SpinLock::new(SerialPort::new(COM1));

#[doc(hidden)]
pub fn _serial_print(args: fmt::Arguments) {
    use core::fmt::Write;
    let mut port = SERIAL1.lock();
    port.write_fmt(args).unwrap();
}

#[macro_export]
macro_rules! serial_print {
    ($($arg:tt)*) => {
        $crate::drivers::serial::_serial_print(format_args!($($arg)*))
    };
}

#[macro_export]
macro_rules! serial_println {
    () => ($crate::serial_print!("\n"));
    ($($arg:tt)*) => ($crate::serial_print!("{}\n", format_args!($($arg)*)));
}
