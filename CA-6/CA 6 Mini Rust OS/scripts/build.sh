#!/usr/bin/env bash
set -e

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure Rust environment is loaded
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
elif [ -f "/root/.cargo/env" ]; then
    source "/root/.cargo/env"
fi
export PATH="$HOME/.cargo/bin:/root/.cargo/bin:$PATH"

echo "=========================================================="
echo "      BUILDING CA-6 MINI RUST OS BARE-METAL KERNEL       "
echo "=========================================================="

# Create necessary directories
mkdir -p build output results screenshots iso/boot/grub

# Step 1: Assemble the Multiboot 64-bit bootloader
echo "[1/5] Assembling arch/x86_64/boot.asm with NASM..."
nasm -f elf64 arch/x86_64/boot.asm -o build/boot.o

# Step 2: Compile the Rust staticlib kernel
echo "[2/5] Compiling Rust kernel staticlib (target: x86_64-unknown-none)..."
cargo build --release --target x86_64-unknown-none

# Step 3: Link into final bare-metal ELF kernel binary
echo "[3/5] Linking kernel with GNU ld using linker.ld..."
ld -n -T linker.ld -o build/kernel.bin build/boot.o target/x86_64-unknown-none/release/libca6_mini_rust_os.a

# Step 4: Verify Multiboot 1 compliance
echo "[4/5] Verifying Multiboot compatibility..."
if grub-file --is-x86-multiboot build/kernel.bin; then
    echo "  -> SUCCESS: build/kernel.bin is a valid Multiboot 1 kernel!"
else
    echo "  -> WARNING: grub-file did not confirm multiboot, continuing with ISO creation..."
fi

# Step 5: Build bootable ISO image with GRUB
echo "[5/5] Generating bootable ISO using grub-mkrescue..."
cp build/kernel.bin iso/boot/kernel.bin

cat << 'EOF' > iso/boot/grub/grub.cfg
set timeout=0
set default=0

menuentry "CA-6 Mini Rust OS" {
    multiboot /boot/kernel.bin
    boot
}
EOF

# Build to temporary ISO file first to preserve any previous ISO until success
rm -f output/os_new.iso
grub-mkrescue -o output/os_new.iso iso 2>/dev/null || grub-mkrescue -o output/os_new.iso iso

if [ -f "output/os_new.iso" ]; then
    if [ -f "output/os.iso" ]; then
        cp -f output/os.iso output/os.iso.prev 2>/dev/null || true
        rm -f output/os.iso 2>/dev/null || true
    fi
    mv output/os_new.iso output/os.iso 2>/dev/null || cp -f output/os_new.iso output/os.iso
    rm -f output/os_new.iso 2>/dev/null || true
    ISO_SIZE=$(du -h output/os.iso | cut -f1)
    echo "=========================================================="
    echo "  BUILD SUCCESSFUL!"
    echo "  Generated ISO: output/os.iso (Size: $ISO_SIZE)"
    echo "=========================================================="
else
    echo "ERROR: Failed to generate output/os.iso"
    exit 1
fi
