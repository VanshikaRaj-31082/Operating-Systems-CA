use core::arch::asm;

const PCI_CONFIG_ADDR: u16 = 0x0CF8;
const PCI_CONFIG_DATA: u16 = 0x0CFC;

#[derive(Clone, Copy)]
pub struct NicInfo {
    pub bus: u8,
    pub device: u8,
    pub function: u8,
    pub vendor_id: u16,
    pub device_id: u16,
    pub class_code: u8,
    pub subclass: u8,
    pub prog_if: u8,
    pub bar0: u32,
    pub irq: u8,
}

unsafe fn outl(port: u16, val: u32) {
    asm!("out dx, eax", in("dx") port, in("eax") val, options(nomem, nostack, preserves_flags));
}

unsafe fn inl(port: u16) -> u32 {
    let ret: u32;
    asm!("in eax, dx", out("eax") ret, in("dx") port, options(nomem, nostack, preserves_flags));
    ret
}

pub fn pci_read_u32(bus: u8, device: u8, function: u8, offset: u8) -> u32 {
    let addr: u32 = (1u32 << 31)
        | ((bus as u32) << 16)
        | (((device & 0x1F) as u32) << 11)
        | (((function & 0x07) as u32) << 8)
        | ((offset & 0xFC) as u32);
    unsafe {
        outl(PCI_CONFIG_ADDR, addr);
        inl(PCI_CONFIG_DATA)
    }
}

pub fn pci_write_u32(bus: u8, device: u8, function: u8, offset: u8, val: u32) {
    let addr: u32 = (1u32 << 31)
        | ((bus as u32) << 16)
        | (((device & 0x1F) as u32) << 11)
        | (((function & 0x07) as u32) << 8)
        | ((offset & 0xFC) as u32);
    unsafe {
        outl(PCI_CONFIG_ADDR, addr);
        outl(PCI_CONFIG_DATA, val);
    }
}

pub fn pci_enable_bus_master(bus: u8, device: u8, function: u8) {
    let cmd = pci_read_u32(bus, device, function, 0x04);
    // Bit 0: I/O Space, Bit 1: Memory Space, Bit 2: Bus Master
    pci_write_u32(bus, device, function, 0x04, cmd | 0x0007);
}

pub fn controller_name(vendor_id: u16, device_id: u16) -> &'static str {
    match (vendor_id, device_id) {
        (0x1022, 0x2000) => "AMD PCnet-FAST III (Am79C973)",
        (0x8086, 0x100E) => "Intel PRO/1000 MT (82540EM)",
        (0x8086, 0x100F) => "Intel PRO/1000 MT Server (82545EM)",
        (0x8086, 0x10D3) => "Intel PRO/1000 PT Desktop (82574L)",
        (0x1AF4, 0x1000) => "Virtio Network Device (Legacy)",
        (0x1AF4, 0x1041) => "Virtio Network Device (Modern)",
        (0x10EC, 0x8139) => "Realtek RTL8139 Fast Ethernet",
        (0x10EC, 0x8168) => "Realtek RTL8111/8168 Gigabit Ethernet",
        _ => "Unclassified PCI Ethernet Controller",
    }
}

pub fn detect_network_adapters(out: &mut [Option<NicInfo>; 8]) -> usize {
    let mut found = 0usize;
    for bus in 0u8..=7 {
        for device in 0u8..32 {
            let vendor_device = pci_read_u32(bus, device, 0, 0x00);
            let vendor_id = (vendor_device & 0xFFFF) as u16;
            if vendor_id == 0xFFFF {
                continue;
            }
            let _device_id = ((vendor_device >> 16) & 0xFFFF) as u16;

            let header_type = ((pci_read_u32(bus, device, 0, 0x0C) >> 16) & 0xFF) as u8;
            let max_funcs: u8 = if (header_type & 0x80) != 0 { 8 } else { 1 };

            for function in 0..max_funcs {
                let vd = if function == 0 {
                    vendor_device
                } else {
                    pci_read_u32(bus, device, function, 0x00)
                };
                let vid = (vd & 0xFFFF) as u16;
                if vid == 0xFFFF {
                    continue;
                }
                let did = ((vd >> 16) & 0xFFFF) as u16;
                let class_reg = pci_read_u32(bus, device, function, 0x08);
                let class_code = ((class_reg >> 24) & 0xFF) as u8;
                let subclass = ((class_reg >> 16) & 0xFF) as u8;
                let prog_if = ((class_reg >> 8) & 0xFF) as u8;

                // Class 0x02 = Network Controller, Subclass 0x00 = Ethernet
                if class_code == 0x02 && subclass == 0x00 && found < out.len() {
                    let bar0 = pci_read_u32(bus, device, function, 0x10);
                    let intr = pci_read_u32(bus, device, function, 0x3C);
                    let irq = (intr & 0xFF) as u8;

                    out[found] = Some(NicInfo {
                        bus,
                        device,
                        function,
                        vendor_id: vid,
                        device_id: did,
                        class_code,
                        subclass,
                        prog_if,
                        bar0,
                        irq,
                    });
                    found += 1;
                }
            }
        }
    }
    found
}

pub fn print_network_status() {
    use crate::drivers::vga::{Color, WRITER};
    use crate::println;

    {
        let mut w = WRITER.lock();
        w.set_color(Color::LightCyan, Color::Black);
    }
    println!("\n--- PCI Network Controller Probe (Bus 0..7) ---");

    let mut nics: [Option<NicInfo>; 8] = [None; 8];
    let count = detect_network_adapters(&mut nics);

    if count == 0 {
        {
            let mut w = WRITER.lock();
            w.set_color(Color::LightRed, Color::Black);
        }
        println!("[NET] Adapter Status : NOT DETECTED on scanned PCI buses");
        println!("[NET] Link State     : No Ethernet controller found");
    } else {
        for i in 0..count {
            if let Some(nic) = nics[i] {
                {
                    let mut w = WRITER.lock();
                    w.set_color(Color::LightGreen, Color::Black);
                }
                println!(
                    "[NET] NIC #{} Detected : {} ({:04x}:{:04x}) at {:02x}:{:02x}.{}",
                    i,
                    controller_name(nic.vendor_id, nic.device_id),
                    nic.vendor_id,
                    nic.device_id,
                    nic.bus,
                    nic.device,
                    nic.function
                );
                {
                    let mut w = WRITER.lock();
                    w.set_color(Color::Yellow, Color::Black);
                }
                println!(
                    "[NET] PCI Class      : 0x{:02x}/0x{:02x} (prog-if 0x{:02x}), IRQ: {}",
                    nic.class_code, nic.subclass, nic.prog_if, nic.irq
                );
                println!(
                    "[NET] BAR0 MMIO      : {:#010x} ({})",
                    nic.bar0,
                    if (nic.bar0 & 1) == 0 { "Memory-Mapped I/O" } else { "I/O Port" }
                );
                println!(
                    "[NET] Link/Stack     : PCI Device Present (MAC/PHY/IP driver not loaded)"
                );
            }
        }
    }

    {
        let mut w = WRITER.lock();
        w.set_color(Color::White, Color::Black);
    }
}
