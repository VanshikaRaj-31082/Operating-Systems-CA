#!/usr/bin/env bash
set -e

echo "=== Updating apt and installing dependencies ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y build-essential nasm qemu-system-x86 grub-pc-bin grub-common xorriso mtools curl git gcc-multilib

echo "=== Installing Rust for default user and root ==="
if ! command -v rustup >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
fi

source "$HOME/.cargo/env" || true
export PATH="$HOME/.cargo/bin:$PATH"

rustup target add x86_64-unknown-none

# Also ensure regular user has rustup in PATH if home directory exists
USER_HOME=$(eval echo ~${SUDO_USER:-vanshika31082})
if [ -d "$USER_HOME" ]; then
    echo "Configuring for user in $USER_HOME"
    cp -r "$HOME/.cargo" "$USER_HOME/" || true
    cp -r "$HOME/.rustup" "$USER_HOME/" || true
    chown -R ${SUDO_USER:-vanshika31082}:${SUDO_USER:-vanshika31082} "$USER_HOME/.cargo" "$USER_HOME/.rustup" || true
fi

echo "=== Verification ==="
nasm -v
qemu-system-x86_64 --version
grub-mkrescue --version
xorriso --version
rustc --version
cargo --version
rustup target list | grep installed
