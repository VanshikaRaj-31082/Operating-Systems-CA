#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ISO_PATH="output/os.iso"
SERIAL_LOG="results/qemu_serial.log"
SCREENSHOT_PPM="screenshots/qemu_screen.ppm"
SCREENSHOT_PNG="screenshots/qemu_screen.png"

mkdir -p results screenshots

if [ ! -f "$ISO_PATH" ]; then
    echo "ERROR: $ISO_PATH not found! Run scripts/build.sh first."
    exit 1
fi

echo "=========================================================="
echo "          RUNNING CA-6 MINI RUST OS IN QEMU               "
echo "=========================================================="
echo "Booting ISO: $ISO_PATH"
echo "Logging serial output to: $SERIAL_LOG"

# Remove old logs
rm -f "$SERIAL_LOG" "$SCREENSHOT_PPM"

# Run QEMU with serial redirected to file and monitor on a unix/tcp socket or stdio
# We run QEMU with a timeout to allow full boot and task scheduler execution
qemu-system-x86_64 \
    -cdrom "$ISO_PATH" \
    -serial file:"$SERIAL_LOG" \
    -display none \
    -no-reboot \
    -no-shutdown \
    -monitor telnet:127.0.0.1:45454,server,nowait &
QEMU_PID=$!

echo "QEMU started with PID $QEMU_PID. Waiting for kernel execution..."
sleep 4

# Connect to monitor to take screendump
if nc -z 127.0.0.1 45454 2>/dev/null || true; then
    (echo "screendump $SCREENSHOT_PPM"; sleep 1; echo "quit") | nc -N 127.0.0.1 45454 2>/dev/null || true
fi

# Kill QEMU after capturing execution
kill $QEMU_PID 2>/dev/null || true
wait $QEMU_PID 2>/dev/null || true

echo "=========================================================="
echo "          QEMU EXECUTION COMPLETED                        "
echo "=========================================================="

if [ -f "$SERIAL_LOG" ]; then
    echo "--- KERNEL CONSOLE OUTPUT (from $SERIAL_LOG) ---"
    cat "$SERIAL_LOG"
    echo "------------------------------------------------"

    if grep -q "ALL SUBSYSTEM TESTS" "$SERIAL_LOG"; then
        echo ">>> VERIFICATION PASSED: Kernel booted and completed all tests!"
    else
        echo ">>> WARNING: Kernel did not reach the completion banner."
    fi
else
    echo "ERROR: Serial log was not generated."
    exit 1
fi
