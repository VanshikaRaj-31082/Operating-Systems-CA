use crate::drivers::e1000::E1000;
use crate::drivers::keyboard::{read_char, KBD_DIAG};
use crate::drivers::pci;
use crate::drivers::vga::{Color, WRITER};
use crate::net::{send_dhcp_discover, poll_dhcp_offer, send_icmp_echo, poll_icmp_reply, NET_STACK};
use crate::scheduler::run_scheduler_demo;
use crate::timer::read_tsc;

const MAX_CMD_LEN: usize = 64;

pub fn run_shell() -> ! {
    {
        let mut w = WRITER.lock();
        w.set_color(Color::LightCyan, Color::Black);
    }
    crate::println!("\n================================================================");
    crate::println!("          CA-6 MINI RUST OS -- INTERACTIVE CONSOLE             ");
    crate::println!("  Type 'help' for commands. Type 'kbd' for keyboard diagnostics.");
    crate::println!("================================================================");

    let mut buf = [0u8; MAX_CMD_LEN];
    let mut len = 0usize;

    print_prompt();

    loop {
        if let Some(ch) = read_char() {
            match ch {
                '\n' => {
                    crate::println!();
                    if len > 0 {
                        if let Ok(cmd) = core::str::from_utf8(&buf[..len]) {
                            execute_command(cmd.trim());
                        }
                        len = 0;
                    }
                    print_prompt();
                }
                '\x08' => {
                    // Backspace
                    if len > 0 {
                        len -= 1;
                        // Destructive backspace: erase character from VGA and serial
                        crate::print!("\x08");
                    }
                }
                c => {
                    if len < MAX_CMD_LEN - 1 && (c as u32) >= 32 && (c as u32) <= 126 {
                        buf[len] = c as u8;
                        len += 1;
                        crate::print!("{}", c);
                    }
                }
            }
        }
        core::hint::spin_loop();
    }
}

fn print_prompt() {
    let mut w = WRITER.lock();
    w.set_color(Color::LightGreen, Color::Black);
    crate::print!("ca6-os> ");
    w.set_color(Color::White, Color::Black);
}

fn execute_command(cmd: &str) {
    let mut parts = cmd.split_ascii_whitespace();
    let main_cmd = match parts.next() {
        Some(c) => c,
        None => return,
    };
    let sub_cmd = parts.next().unwrap_or("");

    match main_cmd {
        "help" => {
            crate::println!("Available commands:");
            crate::println!("  help            - Display this command reference");
            crate::println!("  clear           - Clear VGA display buffer");
            crate::println!("  pci             - Scan PCI buses and list network devices");
            crate::println!("  kbd             - Show keyboard controller diagnostic status");
            crate::println!("  net             - Show complete network controller status");
            crate::println!("  net status      - Check physical/emulated link connectivity");
            crate::println!("  net mac         - Display hardware MAC address");
            crate::println!("  net dhcp        - Trigger DHCP discover and lease renewal");
            crate::println!("  ip              - Display current IPv4 configuration");
            crate::println!("  ping [ip]       - Transmit ICMP Echo Request to gateway");
            crate::println!("  ticks / uptime  - Read CPU Time Stamp Counter (RDTSC)");
            crate::println!("  scheduler       - Re-run Round Robin multi-task demo");
            crate::println!("  reboot          - Perform hardware system reset");
        }
        "clear" => {
            WRITER.lock().clear_screen();
        }
        "kbd" => {
            let diag = KBD_DIAG.lock();
            crate::println!("--- PS/2 Keyboard Diagnostic Status ---");
            crate::println!("Controller Init : {}", if diag.initialized { "YES (Ready)" } else { "NO" });
            crate::println!("Config Read/Set : {:#04x} -> {:#04x}", diag.config_read, diag.config_set);
            crate::println!("Scanning ACK    : {:#04x}", diag.scan_ack);
            crate::println!("Total Scancodes : {}", diag.total_scancodes);
            crate::println!("Last Scancode   : {:#04x}", diag.last_scancode);
            crate::println!("Total Keys      : {}", diag.total_keys);
            crate::println!("Last Decoded    : '{}'", diag.last_char);
        }
        "pci" => {
            pci::print_network_status();
        }
        "net" => {
            match sub_cmd {
                "mac" => {
                    let d = E1000.lock();
                    crate::println!("Hardware MAC: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
                        d.mac[0], d.mac[1], d.mac[2], d.mac[3], d.mac[4], d.mac[5]);
                }
                "status" => {
                    let mut d = E1000.lock();
                    let link = d.update_link_status();
                    let speed = d.link_speed_mbps;
                    if link {
                        crate::println!("[NET] Physical Link: CONNECTED (Speed: {} Mbps)", speed);
                    } else {
                        crate::println!("[NET] Physical Link: DISCONNECTED / NOT DETECTED");
                    }
                }
                "dhcp" => {
                    let mac = E1000.lock().mac;
                    crate::println!("[DHCP] Transmitting DHCP Discover...");
                    if send_dhcp_discover(mac, 0xCA600002) {
                        if let Some(cfg) = poll_dhcp_offer(0xCA600002, 2_000_000) {
                            NET_STACK.lock().config = cfg;
                            crate::println!("[DHCP] Success! IP: {}.{}.{}.{}, Gateway: {}.{}.{}.{}",
                                cfg.ip[0], cfg.ip[1], cfg.ip[2], cfg.ip[3],
                                cfg.gateway[0], cfg.gateway[1], cfg.gateway[2], cfg.gateway[3]);
                        } else {
                            crate::println!("[DHCP] Timed out waiting for DHCP Offer.");
                        }
                    }
                }
                _ => {
                    let d = E1000.lock();
                    let stack = NET_STACK.lock();
                    crate::println!("--- Network Diagnostic Summary ---");
                    crate::println!("Controller : Intel PRO/1000 MT (82540EM)");
                    crate::println!("MMIO Base  : {:#010x}", d.mmio_base);
                    crate::println!("HW MAC     : {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
                        d.mac[0], d.mac[1], d.mac[2], d.mac[3], d.mac[4], d.mac[5]);
                    crate::println!("Link State : {}", if d.link_up { "CONNECTED (Cable OK)" } else { "NOT DETECTED" });
                    crate::println!("Assigned IP: {}.{}.{}.{}",
                        stack.config.ip[0], stack.config.ip[1], stack.config.ip[2], stack.config.ip[3]);
                    crate::println!("TX Packets : {}, RX Packets: {}", stack.tx_count, stack.rx_count);
                }
            }
        }
        "ip" => {
            let cfg = NET_STACK.lock().config;
            if cfg.dhcp_configured {
                crate::println!("IPv4 Address    : {}.{}.{}.{}", cfg.ip[0], cfg.ip[1], cfg.ip[2], cfg.ip[3]);
                crate::println!("Subnet Mask     : {}.{}.{}.{}", cfg.subnet_mask[0], cfg.subnet_mask[1], cfg.subnet_mask[2], cfg.subnet_mask[3]);
                crate::println!("Default Gateway : {}.{}.{}.{}", cfg.gateway[0], cfg.gateway[1], cfg.gateway[2], cfg.gateway[3]);
                crate::println!("DNS Server      : {}.{}.{}.{}", cfg.dns[0], cfg.dns[1], cfg.dns[2], cfg.dns[3]);
            } else {
                crate::println!("No dynamic IP assigned yet. Type 'net dhcp' to lease via VirtualBox NAT.");
            }
        }
        "ping" => {
            let d = E1000.lock();
            let cfg = NET_STACK.lock().config;
            let mac = d.mac;
            drop(d);

            let target_ip = if cfg.dhcp_configured { cfg.gateway } else { [10, 0, 2, 2] };
            let src_ip = if cfg.dhcp_configured { cfg.ip } else { [10, 0, 2, 15] };
            let gateway_mac = [0x52, 0x54, 0x00, 0x12, 0x35, 0x02];

            crate::println!("[PING] Sending 64 bytes to {}.{}.{}.{}...", target_ip[0], target_ip[1], target_ip[2], target_ip[3]);
            let tsc1 = read_tsc();
            if send_icmp_echo(mac, gateway_mac, src_ip, target_ip, 2) {
                if poll_icmp_reply(2_000_000) {
                    let cycles = read_tsc().saturating_sub(tsc1);
                    crate::println!("[PING] Reply from {}.{}.{}.{}: cycles={}", target_ip[0], target_ip[1], target_ip[2], target_ip[3], cycles);
                } else {
                    crate::println!("[PING] Request timed out.");
                }
            } else {
                crate::println!("[PING] Transmission failed.");
            }
        }
        "ticks" | "uptime" => {
            crate::println!("Hardware RDTSC Clock: {} cycles", read_tsc());
        }
        "scheduler" => {
            run_scheduler_demo();
        }
        "reboot" => {
            crate::println!("Resetting system via PS/2 controller...");
            unsafe {
                crate::drivers::serial::outb(0x64, 0xFE);
            }
        }
        unknown => {
            crate::println!("Unknown command: '{}'. Type 'help' for command list.", unknown);
        }
    }
}
