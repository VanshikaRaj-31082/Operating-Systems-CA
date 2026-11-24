"""
CA2 - Deadlock Detection and Avoidance
Configuration: canonical matrices, dimensional parameters, and PRNG seeds.

This module contains:
    - Deterministic PRNG seed for reproducible experiments.
    - Canonical Silberschatz Chapter 8 matrices for baseline verification.
    - Dimensional scaling parameters for benchmark experiments.
    - Benchmark repetition count.

All canonical matrices are verified against Silberschatz et al.,
"Operating System Concepts", Chapter 8 (Deadlocks).
"""

# ── PRNG Seed for Deterministic Reproducibility ──────────────────────────────
# Every synthetic matrix generator uses this seed so that experimental
# results are 100% reproducible across runs.
DEFAULT_SEED = 42

# ── Canonical Silberschatz Example (Chapter 8) ───────────────────────────────
# 5 processes (P0–P4), 3 resource types (A, B, C).
#
# Total system capacity per resource type:
#   A=10, B=5, C=7
#
# Derived values (computed and verified by SystemState):
#   Available = Total - sum(Allocation) = [3, 3, 2]
#   Need = Max - Allocation:
#       P0: [7, 4, 3]
#       P1: [1, 2, 2]
#       P2: [6, 0, 0]
#       P3: [0, 1, 1]
#       P4: [4, 3, 1]
#
# Known safe sequence from initial state: <P1, P3, P4, P0, P2>

SILBERSCHATZ_TOTAL = [10, 5, 7]

SILBERSCHATZ_MAX = [
    [7, 5, 3],  # P0
    [3, 2, 2],  # P1
    [9, 0, 2],  # P2
    [2, 2, 2],  # P3
    [4, 3, 3],  # P4
]

SILBERSCHATZ_ALLOCATION = [
    [0, 1, 0],  # P0
    [2, 0, 0],  # P1
    [3, 0, 2],  # P2
    [2, 1, 1],  # P3
    [0, 0, 2],  # P4
]

# ── Verified Sequential Request Trace ────────────────────────────────────────
# Each request is evaluated against the state produced AFTER all preceding
# requests that were granted have been committed.
#
# Request 1: P1 requests (1, 0, 2) from Available = [3, 3, 2]
#   - (1,0,2) <= Need_P1=(1,2,2)?  Yes
#   - (1,0,2) <= Available=(3,3,2)? Yes
#   - Pretend: Available'=[2,3,0], Alloc'_P1=[3,0,2], Need'_P1=[0,2,0]
#   - Safety check from Work=[2,3,0]:
#       P1: [0,2,0]<=[2,3,0] -> Work=[5,3,2]
#       P3: [0,1,1]<=[5,3,2] -> Work=[7,4,3]
#       P4: [4,3,1]<=[7,4,3] -> Work=[7,4,5]
#       P0: [7,4,3]<=[7,4,5] -> Work=[7,5,5]
#       P2: [6,0,0]<=[7,5,5] -> Work=[10,5,7]
#   - SAFE -> Grant. Committed Available = [2, 3, 0].
#
# Request 2: P0 requests (0, 2, 0) from Available = [2, 3, 0]
#   - (0,2,0) <= Need_P0=(7,4,3)?  Yes
#   - (0,2,0) <= Available=(2,3,0)? Yes  (resources ARE sufficient)
#   - Pretend: Available'=[2,1,0], Alloc'_P0=[0,3,0], Need'_P0=[7,2,3]
#   - Safety check from Work=[2,1,0]:
#       P0: [7,2,3]<=[2,1,0]? No
#       P1: [0,2,0]<=[2,1,0]? No (2>1)
#       P2: [6,0,0]<=[2,1,0]? No (6>2)
#       P3: [0,1,1]<=[2,1,0]? No (1>0)
#       P4: [4,3,1]<=[2,1,0]? No (4>2)
#   - UNSAFE -> Deny and rollback. Available remains [2, 3, 0].
#   - Denial reason: granting leaves system in unsafe state, NOT
#     because of insufficient available resources.

SILBERSCHATZ_REQUESTS = [
    {
        "process": 1,
        "request": [1, 0, 2],
        "expected_outcome": "grant",
        "reason": "Safety check succeeds with sequence <P1, P3, P4, P0, P2>",
        "available_before": [3, 3, 2],
        "available_after": [2, 3, 0],
    },
    {
        "process": 0,
        "request": [0, 2, 0],
        "expected_outcome": "deny",
        "reason": "Resources are available but granting leaves system unsafe",
        "available_before": [2, 3, 0],
        "available_after": [2, 3, 0],  # unchanged due to rollback
    },
]

# ── Dimensional Scaling Parameters ───────────────────────────────────────────
# Used by benchmark experiments to measure algorithmic overhead as
# process count (n) and resource type count (m) increase.
PROCESS_COUNTS = [5, 10, 20, 50, 100]
RESOURCE_TYPE_COUNTS = [3, 5, 10, 20]

# ── Benchmark Parameters ─────────────────────────────────────────────────────
# Minimum number of timed repetitions per configuration for statistical
# validity. Raw measurements, mean, and sample standard deviation are
# recorded for every data point.
BENCHMARK_REPETITIONS = 10

# ── Operational Overhead Experiment ──────────────────────────────────────────
# Number of incremental resource requests in the request-stream simulation.
REQUEST_STREAM_LENGTH = 100

# Interval (in number of requests) between periodic detection sweeps
# in Strategy B.
DETECTION_SWEEP_INTERVAL = 10

