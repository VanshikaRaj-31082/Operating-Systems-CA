use core::fmt;
use core::ptr::write_volatile;
use crate::sync::SpinLock;
use crate::drivers::serial;

#[allow(dead_code)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Color {
    Black = 0,
    Blue = 1,
    Green = 2,
    Cyan = 3,
    Red = 4,
    Magenta = 5,
    Brown = 6,
    LightGray = 7,
    DarkGray = 8,
    LightBlue = 9,
    LightGreen = 10,
    LightCyan = 11,
    LightRed = 12,
    Pink = 13,
    Yellow = 14,
    White = 15,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(transparent)]
pub struct ColorCode(u8);

impl ColorCode {
    pub const fn new(foreground: Color, background: Color) -> ColorCode {
        ColorCode((background as u8) << 4 | (foreground as u8))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(C)]
struct ScreenChar {
    ascii_character: u8,
    color_code: ColorCode,
}

const BUFFER_HEIGHT: usize = 25;
const BUFFER_WIDTH: usize = 80;
const VGA_BUFFER_ADDR: usize = 0xb8000;

#[repr(transparent)]
struct Buffer {
    chars: [[ScreenChar; BUFFER_WIDTH]; BUFFER_HEIGHT],
}

pub struct Writer {
    column_position: usize,
    row_position: usize,
    color_code: ColorCode,
    buffer: *mut Buffer,
}

// Safety: We protect Writer access via SpinLock
unsafe impl Send for Writer {}

impl Writer {
    pub const fn new() -> Self {
        Self {
            column_position: 0,
            row_position: 0,
            color_code: ColorCode::new(Color::White, Color::Black),
            buffer: VGA_BUFFER_ADDR as *mut Buffer,
        }
    }

    pub fn set_color(&mut self, fg: Color, bg: Color) {
        self.color_code = ColorCode::new(fg, bg);
    }

    pub fn write_byte(&mut self, byte: u8) {
        // Echo to serial port as well
        if byte == b'\n' {
            serial::SERIAL1.lock().write_byte(b'\r');
        }
        if byte == 0x08 {
            serial::SERIAL1.lock().write_byte(0x08);
            serial::SERIAL1.lock().write_byte(b' ');
            serial::SERIAL1.lock().write_byte(0x08);
        } else {
            serial::SERIAL1.lock().write_byte(byte);
        }

        match byte {
            b'\n' => self.new_line(),
            0x08 => {
                // Destructive Backspace: move cursor left and clear character
                if self.column_position > 0 {
                    self.column_position -= 1;
                    let row = self.row_position;
                    let col = self.column_position;
                    let color_code = self.color_code;
                    unsafe {
                        let char_ptr = &mut (*self.buffer).chars[row][col] as *mut ScreenChar;
                        write_volatile(
                            char_ptr,
                            ScreenChar {
                                ascii_character: b' ',
                                color_code,
                            },
                        );
                    }
                }
            }
            byte => {
                if self.column_position >= BUFFER_WIDTH {
                    self.new_line();
                }

                let row = self.row_position;
                let col = self.column_position;
                let color_code = self.color_code;

                unsafe {
                    let char_ptr = &mut (*self.buffer).chars[row][col] as *mut ScreenChar;
                    write_volatile(
                        char_ptr,
                        ScreenChar {
                            ascii_character: byte,
                            color_code,
                        },
                    );
                }
                self.column_position += 1;
            }
        }
    }

    pub fn write_string(&mut self, s: &str) {
        for byte in s.bytes() {
            match byte {
                // Printable ASCII, newline, or backspace
                0x20..=0x7e | b'\n' | 0x08 => self.write_byte(byte),
                // Not printable, print a solid block or dot
                _ => self.write_byte(0xfe),
            }
        }
    }

    fn new_line(&mut self) {
        if self.row_position < BUFFER_HEIGHT - 1 {
            self.row_position += 1;
        } else {
            // Scroll up
            for row in 1..BUFFER_HEIGHT {
                for col in 0..BUFFER_WIDTH {
                    unsafe {
                        let character = (*self.buffer).chars[row][col];
                        let target = &mut (*self.buffer).chars[row - 1][col] as *mut ScreenChar;
                        write_volatile(target, character);
                    }
                }
            }
            self.clear_row(BUFFER_HEIGHT - 1);
        }
        self.column_position = 0;
    }

    fn clear_row(&mut self, row: usize) {
        let blank = ScreenChar {
            ascii_character: b' ',
            color_code: self.color_code,
        };
        for col in 0..BUFFER_WIDTH {
            unsafe {
                let target = &mut (*self.buffer).chars[row][col] as *mut ScreenChar;
                write_volatile(target, blank);
            }
        }
    }

    pub fn clear_screen(&mut self) {
        for row in 0..BUFFER_HEIGHT {
            self.clear_row(row);
        }
        self.row_position = 0;
        self.column_position = 0;
    }
}

impl fmt::Write for Writer {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        self.write_string(s);
        Ok(())
    }
}

pub static WRITER: SpinLock<Writer> = SpinLock::new(Writer::new());

#[doc(hidden)]
pub fn _print(args: fmt::Arguments) {
    use core::fmt::Write;
    WRITER.lock().write_fmt(args).unwrap();
}

#[macro_export]
macro_rules! print {
    ($($arg:tt)*) => ($crate::drivers::vga::_print(format_args!($($arg)*)));
}

#[macro_export]
macro_rules! println {
    () => ($crate::print!("\n"));
    ($($arg:tt)*) => ($crate::print!("{}\n", format_args!($($arg)*)));
}
