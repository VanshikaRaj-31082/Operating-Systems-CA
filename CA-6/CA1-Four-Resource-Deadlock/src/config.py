"""Configuration constants and metadata for the Four-Resource Deadlock simulation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
TESTS_DIR = BASE_DIR / "tests"
RESULTS_DIR = BASE_DIR / "results"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# Ensure directories exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ResourceConfig:
    """Configuration for a single-unit non-shareable resource."""
    id: str
    name: str
    rank: int


@dataclass(frozen=True)
class ProcessWorkflow:
    """Configuration for a process workflow."""
    id: str
    name: str
    naive_order: Tuple[str, str]        # (first_resource_id, second_resource_id)
    prevented_order: Tuple[str, str]    # Sorted by resource rank: strictly increasing


# Resources in Challenge D1 (Havender's Total Ordering)
# F(R1) = 1, F(R2) = 2, F(R3) = 3, F(R4) = 4
RESOURCES: Dict[str, ResourceConfig] = {
    "R1": ResourceConfig(id="R1", name="Printer", rank=1),
    "R2": ResourceConfig(id="R2", name="Scanner", rank=2),
    "R3": ResourceConfig(id="R3", name="Database Lock", rank=3),
    "R4": ResourceConfig(id="R4", name="Network Resource", rank=4),
}

# Processes in Challenge D1:
# Naive execution creates the cycle:
# P1(R1 -> R2), P2(R2 -> R3), P3(R3 -> R4), P4(R4 -> R1)
PROCESS_WORKFLOWS: Dict[str, ProcessWorkflow] = {
    "P1": ProcessWorkflow(
        id="P1",
        name="Audit Logger",
        naive_order=("R1", "R2"),
        prevented_order=("R1", "R2"),  # Rank 1 -> Rank 2 (Already ordered)
    ),
    "P2": ProcessWorkflow(
        id="P2",
        name="Document Ingestion",
        naive_order=("R2", "R3"),
        prevented_order=("R2", "R3"),  # Rank 2 -> Rank 3 (Already ordered)
    ),
    "P3": ProcessWorkflow(
        id="P3",
        name="Ledger Sync",
        naive_order=("R3", "R4"),
        prevented_order=("R3", "R4"),  # Rank 3 -> Rank 4 (Already ordered)
    ),
    "P4": ProcessWorkflow(
        id="P4",
        name="Remote Report Dispatcher",
        naive_order=("R4", "R1"),      # VIOLATES HIERARCHY: Rank 4 -> Rank 1
        prevented_order=("R1", "R4"),  # ORDERED FIX: Rank 1 -> Rank 4
    ),
}

# Timing & Watchdog Settings
WORK_DURATION_SECONDS = 0.05       # Time a process simulates holding resources to do work
BARRIER_TIMEOUT_SECONDS = 5.0      # Safety timeout for synchronization barrier
DEADLOCK_TIMEOUT_SECONDS = 2.0     # Time after which stalled execution is confirmed as deadlock
PROCESS_JOIN_TIMEOUT_SECONDS = 4.0 # Child process supervision timeout for safe shutdown

