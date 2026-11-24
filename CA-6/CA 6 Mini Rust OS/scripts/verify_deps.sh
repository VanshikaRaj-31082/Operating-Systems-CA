#!/usr/bin/env bash
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
elif [ -f "/root/.cargo/env" ]; then
    source "/root/.cargo/env"
fi
export PATH="$HOME/.cargo/bin:/root/.cargo/bin:$PATH"

echo "=== RUST TOOLCHAIN ==="
rustc --version || echo "rustc missing"
cargo --version || echo "cargo missing"
rustup target list | grep "installed" || echo "no targets"

echo "=== BUILD TOOLS ==="
nasm -v || echo "nasm missing"
ld -v || echo "ld missing"
grub-mkrescue --version || echo "grub-mkrescue missing"
xorriso -version | head -n 2 || echo "xorriso missing"
