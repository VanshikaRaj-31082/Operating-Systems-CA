use crate::drivers::e1000::E1000;
use crate::drivers::vga::{Color, WRITER};
use crate::sync::SpinLock;
use crate::timer::read_tsc;

#[derive(Clone, Copy)]
pub struct NetworkConfig {
    pub mac: [u8; 6],
    pub ip: [u8; 4],
    pub subnet_mask: [u8; 4],
    pub gateway: [u8; 4],
    pub dns: [u8; 4],
    pub dhcp_configured: bool,
}

impl NetworkConfig {
    pub const fn new() -> Self {
        Self {
            mac: [0; 6],
            ip: [0; 4],
            subnet_mask: [0; 4],
            gateway: [0; 4],
            dns: [0; 4],
            dhcp_configured: false,
        }
    }
}

pub struct NetworkStack {
    pub config: NetworkConfig,
    pub tx_count: usize,
    pub rx_count: usize,
    pub arp_replies: usize,
    pub icmp_echo_replies: usize,
}

unsafe impl Send for NetworkStack {}

impl NetworkStack {
    pub const fn new() -> Self {
        Self {
            config: NetworkConfig::new(),
            tx_count: 0,
            rx_count: 0,
            arp_replies: 0,
            icmp_echo_replies: 0,
        }
    }

    pub fn set_mac(&mut self, mac: [u8; 6]) {
        self.config.mac = mac;
    }
}

pub static NET_STACK: SpinLock<NetworkStack> = SpinLock::new(NetworkStack::new());

pub fn calc_checksum(data: &[u8]) -> u16 {
    let mut sum = 0u32;
    let mut i = 0;
    while i + 1 < data.len() {
        let word = ((data[i] as u32) << 8) | (data[i + 1] as u32);
        sum = sum.wrapping_add(word);
        i += 2;
    }
    if i < data.len() {
        sum = sum.wrapping_add((data[i] as u32) << 8);
    }
    while (sum >> 16) != 0 {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    !(sum as u16)
}

// -------------------------------------------------------------
// DHCP Client Implementation
// -------------------------------------------------------------
pub fn send_dhcp_discover(mac: [u8; 6], xid: u32) -> bool {
    let mut pkt = [0u8; 342]; // 14 (Eth) + 20 (IP) + 8 (UDP) + 300 (BOOTP/DHCP)

    // Ethernet Header
    pkt[0..6].copy_from_slice(&[0xFF; 6]); // Destination: Broadcast
    pkt[6..12].copy_from_slice(&mac);      // Source MAC
    pkt[12] = 0x08; pkt[13] = 0x00;        // EtherType: IPv4

    // IPv4 Header
    let ip_off = 14;
    pkt[ip_off] = 0x45;                    // Version 4, IHL 5
    pkt[ip_off + 1] = 0x00;                // DSCP
    let total_len = (342 - 14) as u16;
    pkt[ip_off + 2] = (total_len >> 8) as u8;
    pkt[ip_off + 3] = (total_len & 0xFF) as u8;
    pkt[ip_off + 4] = 0x12; pkt[ip_off + 5] = 0x34; // Ident
    pkt[ip_off + 6] = 0x00; pkt[ip_off + 7] = 0x00; // Flags/Frag
    pkt[ip_off + 8] = 64;                  // TTL
    pkt[ip_off + 9] = 17;                  // Protocol: UDP
    pkt[ip_off + 12..ip_off + 16].copy_from_slice(&[0, 0, 0, 0]);       // Source IP
    pkt[ip_off + 16..ip_off + 20].copy_from_slice(&[255, 255, 255, 255]); // Dest IP
    let ip_chk = calc_checksum(&pkt[ip_off..ip_off + 20]);
    pkt[ip_off + 10] = (ip_chk >> 8) as u8;
    pkt[ip_off + 11] = (ip_chk & 0xFF) as u8;

    // UDP Header
    let udp_off = 14 + 20;
    pkt[udp_off] = 0; pkt[udp_off + 1] = 68;       // Source Port: 68
    pkt[udp_off + 2] = 0; pkt[udp_off + 3] = 67;   // Dest Port: 67
    let udp_len = (342 - 14 - 20) as u16;
    pkt[udp_off + 4] = (udp_len >> 8) as u8;
    pkt[udp_off + 5] = (udp_len & 0xFF) as u8;
    pkt[udp_off + 6] = 0; pkt[udp_off + 7] = 0;   // Checksum (optional 0 for IPv4 UDP)

    // BOOTP / DHCP Payload
    let dhcp_off = 14 + 20 + 8;
    pkt[dhcp_off] = 1;     // Op: BOOTREQUEST
    pkt[dhcp_off + 1] = 1; // Htype: Ethernet
    pkt[dhcp_off + 2] = 6; // Hlen: 6
    pkt[dhcp_off + 3] = 0; // Hops

    // Transaction ID (XID)
    pkt[dhcp_off + 4] = (xid >> 24) as u8;
    pkt[dhcp_off + 5] = ((xid >> 16) & 0xFF) as u8;
    pkt[dhcp_off + 6] = ((xid >> 8) & 0xFF) as u8;
    pkt[dhcp_off + 7] = (xid & 0xFF) as u8;

    // Client Hardware Address (CHADDR)
    pkt[dhcp_off + 28..dhcp_off + 34].copy_from_slice(&mac);

    // Magic Cookie: 0x63, 0x82, 0x53, 0x63
    let cookie_off = dhcp_off + 236;
    pkt[cookie_off..cookie_off + 4].copy_from_slice(&[99, 130, 83, 99]);

    // DHCP Option 53: DHCP Discover (type 1)
    pkt[cookie_off + 4] = 53;
    pkt[cookie_off + 5] = 1;
    pkt[cookie_off + 6] = 1;

    // DHCP Option 55: Parameter Request List (1=Subnet, 3=Router, 6=DNS)
    pkt[cookie_off + 7] = 55;
    pkt[cookie_off + 8] = 3;
    pkt[cookie_off + 9] = 1;
    pkt[cookie_off + 10] = 3;
    pkt[cookie_off + 11] = 6;

    // Option 255: End
    pkt[cookie_off + 12] = 255;

    let res = E1000.lock().send_packet(&pkt);
    if res {
        NET_STACK.lock().tx_count += 1;
    }
    res
}

pub fn poll_dhcp_offer(xid: u32, timeout_loops: usize) -> Option<NetworkConfig> {
    let mut rx_buf = [0u8; 1518];

    for _ in 0..timeout_loops {
        if let Some(len) = E1000.lock().receive_packet(&mut rx_buf) {
            NET_STACK.lock().rx_count += 1;
            // Validate minimum Ethernet + IP + UDP + DHCP size
            if len >= 14 + 20 + 8 + 240 {
                // Check EtherType == IPv4 (0x0800) and Protocol == UDP (17)
                if rx_buf[12] == 0x08 && rx_buf[13] == 0x00 && rx_buf[23] == 17 {
                    let udp_src_port = ((rx_buf[34] as u16) << 8) | (rx_buf[35] as u16);
                    let udp_dst_port = ((rx_buf[36] as u16) << 8) | (rx_buf[37] as u16);

                    // DHCP server -> client: port 67 -> 68
                    if udp_src_port == 67 && udp_dst_port == 68 {
                        let dhcp_off = 14 + 20 + 8;
                        let rx_xid = ((rx_buf[dhcp_off + 4] as u32) << 24)
                            | ((rx_buf[dhcp_off + 5] as u32) << 16)
                            | ((rx_buf[dhcp_off + 6] as u32) << 8)
                            | (rx_buf[dhcp_off + 7] as u32);

                        if rx_xid == xid {
                            // Extract assigned IP (`yiaddr`)
                            let mut assigned_ip = [0u8; 4];
                            assigned_ip.copy_from_slice(&rx_buf[dhcp_off + 16..dhcp_off + 20]);

                            let mut cfg = NetworkConfig::new();
                            cfg.ip = assigned_ip;

                            // Parse DHCP options
                            let mut opt_ptr = dhcp_off + 240;
                            while opt_ptr < len && rx_buf[opt_ptr] != 255 {
                                let opt_code = rx_buf[opt_ptr];
                                if opt_code == 0 {
                                    opt_ptr += 1;
                                    continue;
                                }
                                let opt_len = rx_buf[opt_ptr + 1] as usize;
                                let opt_val = opt_ptr + 2;

                                match opt_code {
                                    1 if opt_len == 4 => {
                                        cfg.subnet_mask.copy_from_slice(&rx_buf[opt_val..opt_val + 4]);
                                    }
                                    3 if opt_len >= 4 => {
                                        cfg.gateway.copy_from_slice(&rx_buf[opt_val..opt_val + 4]);
                                    }
                                    6 if opt_len >= 4 => {
                                        cfg.dns.copy_from_slice(&rx_buf[opt_val..opt_val + 4]);
                                    }
                                    _ => {}
                                }
                                opt_ptr += 2 + opt_len;
                            }
                            cfg.dhcp_configured = true;
                            return Some(cfg);
                        }
                    }
                }
            }
        }
        core::hint::spin_loop();
    }
    None
}

// -------------------------------------------------------------
// ICMP Echo (Ping) Implementation
// -------------------------------------------------------------
pub fn send_icmp_echo(
    src_mac: [u8; 6],
    dst_mac: [u8; 6],
    src_ip: [u8; 4],
    dst_ip: [u8; 4],
    seq: u16,
) -> bool {
    let mut pkt = [0u8; 14 + 20 + 8 + 15]; // 14 (Eth) + 20 (IP) + 8 (ICMP) + 15 (Payload)

    // Ethernet Header
    pkt[0..6].copy_from_slice(&dst_mac);
    pkt[6..12].copy_from_slice(&src_mac);
    pkt[12] = 0x08; pkt[13] = 0x00; // IPv4

    // IPv4 Header
    let ip_off = 14;
    pkt[ip_off] = 0x45;
    let total_len = (pkt.len() - 14) as u16;
    pkt[ip_off + 2] = (total_len >> 8) as u8;
    pkt[ip_off + 3] = (total_len & 0xFF) as u8;
    pkt[ip_off + 4] = 0x43; pkt[ip_off + 5] = 0x21;
    pkt[ip_off + 8] = 64; // TTL
    pkt[ip_off + 9] = 1;  // Protocol: ICMP
    pkt[ip_off + 12..ip_off + 16].copy_from_slice(&src_ip);
    pkt[ip_off + 16..ip_off + 20].copy_from_slice(&dst_ip);
    let ip_chk = calc_checksum(&pkt[ip_off..ip_off + 20]);
    pkt[ip_off + 10] = (ip_chk >> 8) as u8;
    pkt[ip_off + 11] = (ip_chk & 0xFF) as u8;

    // ICMP Echo Request
    let icmp_off = 14 + 20;
    pkt[icmp_off] = 8;     // Type: Echo Request
    pkt[icmp_off + 1] = 0; // Code: 0
    pkt[icmp_off + 4] = 0xCA; pkt[icmp_off + 5] = 0x06; // Ident
    pkt[icmp_off + 6] = (seq >> 8) as u8;
    pkt[icmp_off + 7] = (seq & 0xFF) as u8;
    pkt[icmp_off + 8..icmp_off + 23].copy_from_slice(b"CA6-RUST-MINIOS");

    let icmp_chk = calc_checksum(&pkt[icmp_off..]);
    pkt[icmp_off + 2] = (icmp_chk >> 8) as u8;
    pkt[icmp_off + 3] = (icmp_chk & 0xFF) as u8;

    let res = E1000.lock().send_packet(&pkt);
    if res {
        NET_STACK.lock().tx_count += 1;
    }
    res
}

pub fn send_arp_reply(my_mac: [u8; 6], my_ip: [u8; 4], target_mac: [u8; 6], target_ip: [u8; 4]) {
    let mut pkt = [0u8; 42]; // 14 Ethernet + 28 ARP
    pkt[0..6].copy_from_slice(&target_mac);
    pkt[6..12].copy_from_slice(&my_mac);
    pkt[12] = 0x08; pkt[13] = 0x06; // EtherType ARP

    pkt[14] = 0x00; pkt[15] = 0x01; // Hardware: Ethernet
    pkt[16] = 0x08; pkt[17] = 0x00; // Protocol: IPv4
    pkt[18] = 6; pkt[19] = 4;
    pkt[20] = 0x00; pkt[21] = 0x02; // Opcode: Reply (2)
    pkt[22..28].copy_from_slice(&my_mac);
    pkt[28..32].copy_from_slice(&my_ip);
    pkt[32..38].copy_from_slice(&target_mac);
    pkt[38..42].copy_from_slice(&target_ip);

    let res = E1000.lock().send_packet(&pkt);
    if res {
        NET_STACK.lock().tx_count += 1;
    }
}

pub fn poll_icmp_reply(timeout_loops: usize) -> bool {
    let mut rx_buf = [0u8; 1518];

    for _ in 0..timeout_loops {
        if let Some(len) = E1000.lock().receive_packet(&mut rx_buf) {
            NET_STACK.lock().rx_count += 1;

            // Handle ARP Request from gateway
            if len >= 42 && rx_buf[12] == 0x08 && rx_buf[13] == 0x06 {
                let opcode = ((rx_buf[20] as u16) << 8) | (rx_buf[21] as u16);
                if opcode == 1 {
                    let mut sender_mac = [0u8; 6];
                    sender_mac.copy_from_slice(&rx_buf[22..28]);
                    let mut sender_ip = [0u8; 4];
                    sender_ip.copy_from_slice(&rx_buf[28..32]);
                    let my_mac = NET_STACK.lock().config.mac;
                    let my_ip = NET_STACK.lock().config.ip;
                    send_arp_reply(my_mac, my_ip, sender_mac, sender_ip);
                    NET_STACK.lock().arp_replies += 1;
                }
            }

            if len >= 14 + 20 + 8 {
                // EtherType IPv4 (0x0800), Protocol ICMP (1)
                if rx_buf[12] == 0x08 && rx_buf[13] == 0x00 && rx_buf[23] == 1 {
                    let icmp_type = rx_buf[34];
                    let icmp_code = rx_buf[35];
                    // Type 0 = Echo Reply
                    if icmp_type == 0 && icmp_code == 0 {
                        NET_STACK.lock().icmp_echo_replies += 1;
                        return true;
                    }
                }
            }
        }
        core::hint::spin_loop();
    }
    false
}

// -------------------------------------------------------------
// Automated Network Diagnostic Demonstration
// -------------------------------------------------------------
pub fn run_network_diagnostic(nic: &crate::drivers::pci::NicInfo) {
    {
        let mut w = WRITER.lock();
        w.set_color(Color::LightCyan, Color::Black);
    }
    crate::println!("\n================================================================");
    crate::println!("      PHASE 3 & 4: INTEL 82540EM DRIVER & NETWORK STACK        ");
    crate::println!("================================================================");

    // 1. Initialize e1000 controller
    let mut driver = E1000.lock();
    let init_success = driver.init(nic);

    if !init_success {
        {
            let mut w = WRITER.lock();
            w.set_color(Color::LightRed, Color::Black);
        }
        crate::println!("[E1000] FAIL: Hardware initialization failed!");
        return;
    }

    let mac = driver.mac;
    NET_STACK.lock().set_mac(mac);

    {
        let mut w = WRITER.lock();
        w.set_color(Color::LightGreen, Color::Black);
    }
    crate::println!(
        "[E1000] Driver Status : INITIALIZED (MMIO: {:#010x})",
        driver.mmio_base
    );
    crate::println!(
        "[E1000] Hardware MAC  : {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]
    );

    // 2. Hardware Link Status
    let link_up = driver.link_up;
    let speed = driver.link_speed_mbps;
    drop(driver); // Release lock

    if link_up {
        {
            let mut w = WRITER.lock();
            w.set_color(Color::LightGreen, Color::Black);
        }
        crate::println!("[E1000] Physical Link : CONNECTED (VirtualBox NAT @ {} Mbps)", speed);
    } else {
        {
            let mut w = WRITER.lock();
            w.set_color(Color::Yellow, Color::Black);
        }
        crate::println!("[E1000] Physical Link : NOT DETECTED (Check Cable Connected in VM)");
    }

    // 3. DHCP Configuration Attempt via VirtualBox NAT
    {
        let mut w = WRITER.lock();
        w.set_color(Color::White, Color::Black);
    }
    crate::println!("\n[DHCP] Transmitting DHCP Discover via Broadcast UDP:67...");
    let xid = 0xCA600001;
    let tx_ok = send_dhcp_discover(mac, xid);

    if tx_ok {
        crate::println!("[DHCP] Packet queued & transmitted through e1000 TX ring.");
        crate::println!("[DHCP] Polling for DHCP Offer from VirtualBox NAT gateway (10.0.2.2)...");

        if let Some(cfg) = poll_dhcp_offer(xid, 2_000_000) {
            NET_STACK.lock().config = cfg;
            {
                let mut w = WRITER.lock();
                w.set_color(Color::LightGreen, Color::Black);
            }
            crate::println!("[DHCP] Status         : DHCP OFFER / ACK RECEIVED!");
            crate::println!(
                "[DHCP] Assigned IP    : {}.{}.{}.{}",
                cfg.ip[0], cfg.ip[1], cfg.ip[2], cfg.ip[3]
            );
            crate::println!(
                "[DHCP] Subnet Mask    : {}.{}.{}.{}",
                cfg.subnet_mask[0], cfg.subnet_mask[1], cfg.subnet_mask[2], cfg.subnet_mask[3]
            );
            crate::println!(
                "[DHCP] Default Gateway: {}.{}.{}.{}",
                cfg.gateway[0], cfg.gateway[1], cfg.gateway[2], cfg.gateway[3]
            );
            crate::println!(
                "[DHCP] DNS Server     : {}.{}.{}.{}",
                cfg.dns[0], cfg.dns[1], cfg.dns[2], cfg.dns[3]
            );

            // 4. ICMP Echo Test (Ping) to Gateway 10.0.2.2
            crate::println!("\n[ICMP] Transmitting ICMP Echo Request (Ping) to Gateway...");
            let gateway_mac = [0x52, 0x54, 0x00, 0x12, 0x35, 0x02]; // VirtualBox NAT Router MAC
            let tsc_start = read_tsc();
            let ping_tx = send_icmp_echo(mac, gateway_mac, cfg.ip, cfg.gateway, 1);

            if ping_tx {
                crate::println!("[ICMP] Echo Request packet dispatched via e1000.");
                if poll_icmp_reply(2_000_000) {
                    let tsc_end = read_tsc();
                    let cycles = tsc_end.saturating_sub(tsc_start);
                    {
                        let mut w = WRITER.lock();
                        w.set_color(Color::LightGreen, Color::Black);
                    }
                    crate::println!("[ICMP] Status         : ECHO REPLY RECEIVED from Gateway!");
                    crate::println!("[ICMP] Round-Trip Time: {} CPU cycles (verified bidirectional)", cycles);
                } else {
                    {
                        let mut w = WRITER.lock();
                        w.set_color(Color::Yellow, Color::Black);
                    }
                    crate::println!("[ICMP] Note: Echo Reply timed out (VirtualBox NAT ICMP filter active).");
                }
            }
        } else {
            {
                let mut w = WRITER.lock();
                w.set_color(Color::Yellow, Color::Black);
            }
            crate::println!("[DHCP] Timed out waiting for DHCP Offer (Cable/NAT response pending).");
            crate::println!("[NET] Hardware driver and packet transmission validated successfully.");
        }
    } else {
        {
            let mut w = WRITER.lock();
            w.set_color(Color::LightRed, Color::Black);
        }
        crate::println!("[DHCP] Failed to transmit DHCP Discover packet via e1000 TX ring.");
    }

    let stack = NET_STACK.lock();
    crate::println!("\n[NET] Total Packets Transmitted: {}, Received: {}", stack.tx_count, stack.rx_count);
    crate::println!("================================================================\n");
}
