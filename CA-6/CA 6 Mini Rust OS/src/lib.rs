#![no_std]
#![no_main]

pub mod drivers;
pub mod kernel;
pub mod memory;
pub mod net;
pub mod scheduler;
pub mod sync;
pub mod task;
pub mod timer;

use core::panic::PanicInfo;
use drivers::vga::{Color, WRITER};
use sync::SpinLock;

#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    // Set text to White on Red
    WRITER.lock().set_color(Color::White, Color::Red);
    println!("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
    println!("                  KERNEL PANIC                          ");
    println!("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
    println!("{}", info);
    loop {
        core::hint::spin_loop();
    }
}

fn test_sync_primitives() -> bool {
    println!("[SYNC] Testing SpinLock mutual exclusion primitive...");
    static TEST_LOCK: SpinLock<usize> = SpinLock::new(42);

    {
        let mut guard = TEST_LOCK.lock();
        *guard += 8;
        if *guard != 50 {
            println!("[SYNC] FAIL: Value mismatch inside lock!");
            return false;
        }
    } // Guard dropped here

    // Test try_lock
    if let Some(guard) = TEST_LOCK.try_lock() {
        if *guard != 50 {
            println!("[SYNC] FAIL: Value mismatch in try_lock!");
            return false;
        }
    } else {
        println!("[SYNC] FAIL: try_lock failed unexpectedly!");
        return false;
    }

    println!("[SYNC] SpinLock test PASSED (RAII lock/unlock verified).");
    true
}

#[no_mangle]
pub extern "C" fn rust_main() -> ! {
    // Initialize serial port first so every log is captured by QEMU
    drivers::serial::SERIAL1.lock().init();

    // Clear VGA screen and display banner
    {
        let mut writer = WRITER.lock();
        writer.clear_screen();
        writer.set_color(Color::LightCyan, Color::Black);
    }

    println!("================================================================");
    println!("        CA-6 MINI RUST OS -- BARE-METAL x86_64 KERNEL           ");
    println!("================================================================");
    
    {
        let mut writer = WRITER.lock();
        writer.set_color(Color::Yellow, Color::Black);
    }
    println!("OS Name   : {}", kernel::info::OS_NAME);
    println!("Version   : {}", kernel::info::VERSION);
    println!("Arch      : {}", kernel::info::ARCH);
    println!("Bootloader: Multiboot 1 (GRUB) -> 64-bit Long Mode Transition");
    println!("Status    : Bare-Metal Kernel Initialized Successfully\n");

    {
        let mut writer = WRITER.lock();
        writer.set_color(Color::White, Color::Black);
    }

    // 1. Synchronization Testing
    test_sync_primitives();

    // 2. Memory Allocator Testing
    memory::run_allocator_tests();

    // 3. Hardware Timer / PIT Setup
    timer::init_timer();

    // 4. Round Robin Scheduler Demonstration
    {
        let mut writer = WRITER.lock();
        writer.set_color(Color::LightGreen, Color::Black);
    }
    scheduler::run_scheduler_demo();

    // 5. PCI Network Controller Detection & Driver Initialization
    drivers::pci::print_network_status();

    // Check if an Ethernet controller was discovered and initialize it
    let mut nics: [Option<drivers::pci::NicInfo>; 8] = [None; 8];
    let count = drivers::pci::detect_network_adapters(&mut nics);
    if count > 0 {
        if let Some(nic) = nics[0] {
            net::run_network_diagnostic(&nic);
        }
    } else {
        println!("\n[NET] No PCI Ethernet controller found. Skipping driver & DHCP.");
    }

    // 6. Initialize Keyboard Hardware in Polling Mode
    drivers::keyboard::init_keyboard();

    // 7. Enter Interactive Shell (or Fallback to Halting Loop)
    kernel::shell::run_shell();
}
