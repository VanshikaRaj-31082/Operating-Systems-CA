#![allow(dead_code)]
use crate::drivers::serial::{inb, outb};
use crate::sync::SpinLock;

const PS2_DATA_PORT: u16    = 0x60;
const PS2_STATUS_PORT: u16  = 0x64;
const PS2_COMMAND_PORT: u16 = 0x64;

// PS/2 Controller Commands
const CMD_READ_CONFIG: u8  = 0x20;
const CMD_WRITE_CONFIG: u8 = 0x60;
const CMD_DISABLE_MOUSE: u8 = 0xA7;
const CMD_ENABLE_MOUSE: u8  = 0xA8;
const CMD_DISABLE_KBD: u8  = 0xAD;
const CMD_ENABLE_KBD: u8   = 0xAE;

// Keyboard Device Commands
const KBD_CMD_ENABLE_SCAN: u8 = 0xF4;
const KBD_RESP_ACK: u8        = 0xFA;

// Scancode Set 1 standard mapping (indices 0x00 to 0x39)
static SCANCODE_MAP: [char; 128] = [
    '\0', '\x1B', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\x08', // 0x00 - 0x0E
    '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',           // 0x0F - 0x1C
    '\0', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`',                // 0x1D - 0x29
    '\0', '\\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/',                      // 0x2A - 0x35
    '\0', '*', '\0', ' ',                                                               // 0x36 - 0x39
    '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',                         // 0x3A - 0x43
    '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',                         // 0x44 - 0x4D
    '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',                         // 0x4E - 0x57
    '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',                         // 0x58 - 0x61
    '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',                         // 0x62 - 0x6B
    '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',                         // 0x6C - 0x75
    '\0', '\0', '\0', '\0', '\0', '\0',                                                 // 0x76 - 0x7B
    '\0', '\0', '\0', '\0',                                                             // 0x7C - 0x7F
];

#[derive(Clone, Copy)]
pub struct KeyboardDiagnostics {
    pub initialized: bool,
    pub config_read: u8,
    pub config_set: u8,
    pub scan_ack: u8,
    pub total_scancodes: usize,
    pub last_scancode: u8,
    pub total_keys: usize,
    pub last_char: char,
}

impl KeyboardDiagnostics {
    pub const fn new() -> Self {
        Self {
            initialized: false,
            config_read: 0,
            config_set: 0,
            scan_ack: 0,
            total_scancodes: 0,
            last_scancode: 0,
            total_keys: 0,
            last_char: '\0',
        }
    }
}

pub static KBD_DIAG: SpinLock<KeyboardDiagnostics> = SpinLock::new(KeyboardDiagnostics::new());
static mut SHIFT_ACTIVE: bool = false;
static mut EXTENDED_PREFIX: bool = false;

fn io_wait() {
    unsafe {
        outb(0x80, 0);
    }
}

fn wait_input_buffer_empty() -> bool {
    let mut timeout = 100_000;
    unsafe {
        while (inb(PS2_STATUS_PORT) & 0x02) != 0 {
            timeout -= 1;
            if timeout == 0 {
                return false;
            }
            core::hint::spin_loop();
        }
    }
    true
}

fn wait_output_buffer_full() -> bool {
    let mut timeout = 100_000;
    unsafe {
        while (inb(PS2_STATUS_PORT) & 0x01) == 0 {
            timeout -= 1;
            if timeout == 0 {
                return false;
            }
            core::hint::spin_loop();
        }
    }
    true
}

pub fn drain_output_buffer() {
    let mut timeout = 1000;
    unsafe {
        while (inb(PS2_STATUS_PORT) & 0x01) != 0 && timeout > 0 {
            let _ = inb(PS2_DATA_PORT);
            io_wait();
            timeout -= 1;
        }
    }
}

/// Fully initializes the 8042 PS/2 controller and keyboard hardware for polled operation.
pub fn init_keyboard() -> bool {
    crate::println!("[KBD] Initializing 8042 PS/2 Keyboard Controller...");
    crate::serial_println!("[KBD] Initializing 8042 PS/2 Keyboard Controller...");

    unsafe {
        // Step 1: Drain any stale bytes left in the output buffer by BIOS/GRUB
        drain_output_buffer();

        // Step 2: Disable both ports temporarily during configuration
        if !wait_input_buffer_empty() { return false; }
        outb(PS2_COMMAND_PORT, CMD_DISABLE_KBD);
        io_wait();

        if !wait_input_buffer_empty() { return false; }
        outb(PS2_COMMAND_PORT, CMD_DISABLE_MOUSE);
        io_wait();

        drain_output_buffer();

        // Step 3: Read Controller Configuration Byte
        if !wait_input_buffer_empty() { return false; }
        outb(PS2_COMMAND_PORT, CMD_READ_CONFIG);
        io_wait();

        if !wait_output_buffer_full() { return false; }
        let orig_config = inb(PS2_DATA_PORT);

        // Step 4: Configure for clean Polling Mode:
        // Clear Bit 0: Disable IRQ 1 (we use robust polling; no IDT required)
        // Clear Bit 1: Disable IRQ 12 (mouse)
        // Clear Bit 4: Enable Port 1 clock (0 = enabled)
        // Set   Bit 6: Enable translation to Scancode Set 1 (1 = enabled)
        let mut new_config = orig_config;
        new_config &= !(1 << 0); // Disable keyboard interrupt
        new_config &= !(1 << 1); // Disable mouse interrupt
        new_config &= !(1 << 4); // Enable Port 1 interface clock
        new_config |= 1 << 6;  // Enable translation to Scancode Set 1

        if !wait_input_buffer_empty() { return false; }
        outb(PS2_COMMAND_PORT, CMD_WRITE_CONFIG);
        io_wait();

        if !wait_input_buffer_empty() { return false; }
        outb(PS2_DATA_PORT, new_config);
        io_wait();

        // Step 5: Enable First PS/2 Port (Keyboard)
        if !wait_input_buffer_empty() { return false; }
        outb(PS2_COMMAND_PORT, CMD_ENABLE_KBD);
        io_wait();

        drain_output_buffer();

        // Step 6: Send Enable Scanning (0xF4) command to the keyboard device itself.
        // In VirtualBox, if fScanning was false (e.g. after BIOS/GRUB 0xF5), key events
        // are dropped until 0xF4 is sent!
        if !wait_input_buffer_empty() { return false; }
        outb(PS2_DATA_PORT, KBD_CMD_ENABLE_SCAN);
        io_wait();

        // Wait for keyboard device ACK (0xFA) with timeout
        let mut ack = 0u8;
        let mut ack_timeout = 200_000;
        while ack_timeout > 0 {
            if (inb(PS2_STATUS_PORT) & 0x01) != 0 {
                ack = inb(PS2_DATA_PORT);
                if ack == KBD_RESP_ACK {
                    break;
                }
            }
            ack_timeout -= 1;
            core::hint::spin_loop();
        }

        drain_output_buffer();

        {
            let mut diag = KBD_DIAG.lock();
            diag.initialized = true;
            diag.config_read = orig_config;
            diag.config_set = new_config;
            diag.scan_ack = ack;
        }

        crate::println!(
            "[KBD] Status: INITIALIZED (Config: {:#04x}->{:#04x}, Port 1 ON, Scan ACK: {:#04x})",
            orig_config, new_config, ack
        );
        crate::serial_println!(
            "[KBD] Status: INITIALIZED (Config: {:#04x}->{:#04x}, Port 1 ON, Scan ACK: {:#04x})",
            orig_config, new_config, ack
        );
        true
    }
}

/// Polls for a raw scancode from port 0x60.
/// Checks Status Register (0x64):
/// - Bit 0 must be 1 (Output Buffer Full).
/// - Bit 5 must be 0 (Keyboard data, not mouse).
pub fn read_scancode() -> Option<u8> {
    unsafe {
        let status = inb(PS2_STATUS_PORT);
        // Bit 0: Output buffer full
        if (status & 0x01) != 0 {
            let scancode = inb(PS2_DATA_PORT);
            // Bit 5: 1 = Mouse / Auxiliary device; discard for keyboard
            if (status & 0x20) == 0 {
                let mut diag = KBD_DIAG.lock();
                diag.total_scancodes += 1;
                diag.last_scancode = scancode;
                crate::serial_println!(
                    "[KBD] RAW Scancode: {:#04x} (Status: {:#04x}, Type: {})",
                    scancode, status,
                    if (scancode & 0x80) != 0 { "BREAK" } else { "MAKE" }
                );
                return Some(scancode);
            }
        }
        None
    }
}

/// Reads a scancode and decodes it to an ASCII character.
/// Handles Shift state, Keypad Enter, Backspace, and standard printable keys.
pub fn read_char() -> Option<char> {
    if let Some(scancode) = read_scancode() {
        unsafe {
            // Check for extended scancode prefix (0xE0)
            if scancode == 0xE0 {
                EXTENDED_PREFIX = true;
                return None;
            }

            if EXTENDED_PREFIX {
                EXTENDED_PREFIX = false;
                // Keypad Enter make code is 0xE0 0x1C
                if scancode == 0x1C {
                    return Some('\n');
                }
                return None;
            }

            // Shift key press (Make)
            if scancode == 0x2A || scancode == 0x36 {
                SHIFT_ACTIVE = true;
                return None;
            }

            // Shift key release (Break)
            if scancode == 0xAA || scancode == 0xB6 {
                SHIFT_ACTIVE = false;
                return None;
            }

            // We only process Make codes (bit 7 == 0)
            if (scancode & 0x80) == 0 {
                let idx = scancode as usize;
                if idx < SCANCODE_MAP.len() {
                    let mut ch = SCANCODE_MAP[idx];
                    if ch != '\0' {
                        // Apply Shift translation if active
                        if SHIFT_ACTIVE {
                            ch = match ch {
                                'a'..='z' => (ch as u8 - b'a' + b'A') as char,
                                '1' => '!',
                                '2' => '@',
                                '3' => '#',
                                '4' => '$',
                                '5' => '%',
                                '6' => '^',
                                '7' => '&',
                                '8' => '*',
                                '9' => '(',
                                '0' => ')',
                                '-' => '_',
                                '=' => '+',
                                '[' => '{',
                                ']' => '}',
                                ';' => ':',
                                '\'' => '"',
                                '`' => '~',
                                '\\' => '|',
                                ',' => '<',
                                '.' => '>',
                                '/' => '?',
                                other => other,
                            };
                        }

                        let mut diag = KBD_DIAG.lock();
                        diag.total_keys += 1;
                        diag.last_char = ch;
                        return Some(ch);
                    }
                }
            }
        }
    }
    None
}
