#!/usr/bin/env bash
# ==============================================================================
# Master Experiment Orchestrator for CA5
# Executes the full investigation suite and verifies artifact generation
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA5_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$CA5_DIR"

echo "======================================================================"
echo "    CA5 LINUX SYSTEMS ENGINEERING - EXPERIMENT ORCHESTRATOR           "
echo "======================================================================"
echo "Working Directory: $CA5_DIR"
echo "Host Operating System: $(uname -s) $(uname -r)"
echo "Python Executable: $(command -v python3)"

# Run environmental inspection
bash "$SCRIPT_DIR/inspect_system.sh"

echo ""
echo "Starting Master Concurrency Investigation Runner..."
PYTHONPATH="$CA5_DIR" python3 "$CA5_DIR/src/investigation_runner.py"

echo ""
echo "Verifying Generated Artifacts:"
ls -lh "$CA5_DIR/results/raw/"
ls -lh "$CA5_DIR/results/processed/"
ls -lh "$CA5_DIR/results/logs/"

echo ""
echo "======================================================================"
echo "              ALL CA5 EXPERIMENTS COMPLETED SUCCESSFULLY              "
echo "======================================================================"
