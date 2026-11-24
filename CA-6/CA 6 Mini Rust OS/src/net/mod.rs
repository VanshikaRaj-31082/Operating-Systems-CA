pub mod stack;
pub use stack::{
    poll_dhcp_offer, poll_icmp_reply, run_network_diagnostic, send_arp_reply, send_dhcp_discover,
    send_icmp_echo, NetworkConfig, NetworkStack, NET_STACK,
};
