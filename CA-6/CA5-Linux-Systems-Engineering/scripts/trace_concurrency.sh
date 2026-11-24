#!/usr/bin/env bash
# ==============================================================================
# Linux Concurrency & Context-Switch Tracer
# Monitors a target PID/TID in /proc/<pid>/status and /proc/<pid>/wchan
# ==============================================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <PID> [duration_seconds] [interval_seconds]"
    exit 1
fi

TARGET_PID="$1"
DURATION="${2:-5}"
INTERVAL="${3:-0.5}"

if [ ! -d "/proc/$TARGET_PID" ]; then
    echo "Error: Process $TARGET_PID does not exist in /proc."
    exit 1
fi

echo "Tracing PID $TARGET_PID for $DURATION seconds (sampling every ${INTERVAL}s)..."
printf "%-10s | %-12s | %-12s | %-8s | %-20s\n" "Timestamp" "VoluntaryCS" "NonVolCS" "Threads" "State"
echo "----------------------------------------------------------------------------------"

END_TIME=$((SECONDS + DURATION))

while [ $SECONDS -lt $END_TIME ]; do
    if [ ! -d "/proc/$TARGET_PID" ]; then
        echo "Process $TARGET_PID has terminated."
        break
    fi

    STATUS_FILE="/proc/$TARGET_PID/status"
    VOL=$(grep -w "voluntary_ctxt_switches" "$STATUS_FILE" | awk '{print $2}' || echo "N/A")
    NONVOL=$(grep -w "nonvoluntary_ctxt_switches" "$STATUS_FILE" | awk '{print $2}' || echo "N/A")
    THREADS=$(grep -w "Threads" "$STATUS_FILE" | awk '{print $2}' || echo "N/A")
    STATE=$(grep -w "State" "$STATUS_FILE" | awk '{$1=""; print $0}' | xargs || echo "N/A")

    TIMESTAMP=$(date +"%H:%M:%S.%1N")
    printf "%-10s | %-12s | %-12s | %-8s | %-20s\n" "$TIMESTAMP" "$VOL" "$NONVOL" "$THREADS" "$STATE"
    sleep "$INTERVAL"
done

echo "Tracing complete."
