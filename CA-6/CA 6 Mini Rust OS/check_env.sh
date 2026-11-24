#!/usr/bin/env bash
echo "=== SYSTEM INFO ==="
uname -a
cat /etc/os-release | grep PRETTY_NAME

echo "=== TOOL CHECK ==="
for cmd in rustc cargo rustup qemu-system-x86_64 nasm grub-mkrescue grub-pc-bin xorriso make ld gcc clang; do
    echo -n "$cmd: "
    which $cmd || echo "NOT FOUND"
done

echo "=== RUST TARGETS ==="
if which rustup >/dev/null 2>&1; then
    rustup show
    rustup target list | grep installed || true
fi
