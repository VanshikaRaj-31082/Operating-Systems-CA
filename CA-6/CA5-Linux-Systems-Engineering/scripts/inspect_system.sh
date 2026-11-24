#!/usr/bin/env bash
# ==============================================================================
# Linux System and Hardware Inspection Script
# Complies with CA5 Section 5 (Linux Toolchain) and Section 8 (L25, L27)
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "          CA5 - LINUX SYSTEM & HARDWARE INSPECTION REPORT             "
echo "======================================================================"

echo ""
echo "--- 1. Operating System & Kernel ---"
if [ -f /etc/os-release ]; then
    cat /etc/os-release | grep -E "^(NAME|VERSION|PRETTY_NAME|ID)=" || true
else
    uname -s
fi
echo -n "Kernel Release: " && uname -r
echo -n "Architecture:   " && uname -m
echo -n "Kernel Version: " && uname -v

echo ""
echo "--- 2. CPU Architecture & Topology ---"
if command -v lscpu >/dev/null 2>&1; then
    lscpu | grep -E "(Architecture|Model name|CPU\(s\):|Thread\(s\) per core|Core\(s\) per socket|CPU max MHz|Virtualization)" || true
else
    echo "Logical Processors: $(nproc || grep -c ^processor /proc/cpuinfo)"
    grep "model name" /proc/cpuinfo | head -n 1 || true
fi

echo ""
echo "--- 3. Memory Subsystem (/proc/meminfo) ---"
if [ -f /proc/meminfo ]; then
    grep -E "(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree)" /proc/meminfo || true
elif command -v free >/dev/null 2>&1; then
    free -h || true
fi

echo ""
echo "--- 4. System Load & Run Queue (/proc/loadavg) ---"
if [ -f /proc/loadavg ]; then
    echo -n "Load Average (1m, 5m, 15m) & Active/Total Tasks: "
    cat /proc/loadavg
fi

echo ""
echo "--- 5. Key Systems Utilities Availability ---"
for tool in ps top lscpu vmstat iostat pidstat taskset nice renice kill free uname python3 gcc; do
    printf "%-12s : " "$tool"
    if command -v "$tool" >/dev/null 2>&1; then
        echo "$(command -v "$tool")"
    else
        echo "NOT FOUND"
    fi
done

echo ""
echo "======================================================================"
echo "                     INSPECTION COMPLETE                              "
echo "======================================================================"
