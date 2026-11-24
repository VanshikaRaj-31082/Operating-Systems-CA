"""
CA2 - Deadlock Detection and Avoidance
Performance Benchmarking & Metric Collection Module.

This module provides systematic, fair, and reproducible benchmarking
comparing:
    1. Banker's Algorithm (safety_check - O(m × n²))
    2. Multi-Instance Deadlock Detection (detect_deadlock - O(m × n²))

──────────────────────────────────────────────────────────────────────
METHODOLOGICAL RIGOR & FAIRNESS
──────────────────────────────────────────────────────────────────────

1. High-Resolution Timing:
   Uses time.perf_counter() for nanosecond/microsecond resolution.

2. Isolation of Workload Generation:
   Workload generation (matrix instantiation, invariant validation,
   deep copies) is executed strictly BEFORE timing starts.
   Only the algorithmic execution loop is timed.

3. Separate Warm-up and Measurement:
   Configurable warm-up runs (default: 2) ensure CPU caching, branch
   prediction, and Python interpreter optimization stabilize before
   recording metrics.

4. Statistical Rigor:
   Collects multiple repetitions (default: 10) per configuration.
   Computes mean, median, min, max, and sample standard deviation.

5. Semantics and Input Integrity:
   - Banker's Safety receives SystemState (uses Need = Max - Allocation).
   - Deadlock Detection receives SystemState + Request matrix
     (uses actual outstanding requests, never conflating Request with Need).

6. Structured Export:
   Results can be exported to CSV and JSON with complete metadata
   for reproducibility and downstream visualization.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.bankers_algorithm import safety_check
from src.deadlock_detector import detect_deadlock
from src.models import SystemState
from src.workload_generator import (
    make_deadlocked_workload,
    make_random_request,
    make_safe_state,
    make_state,
    make_state_with_pressure,
    make_unsafe_state,
    make_zero_request,
)


# ═══════════════════════════════════════════════════════════════════════
# Exceptions and Result Schema
# ═══════════════════════════════════════════════════════════════════════


class BenchmarkError(Exception):
    """Raised when benchmark parameters or configurations are invalid."""
    pass


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Immutable container for a single benchmark evaluation point.

    Attributes
    ----------
    algorithm : str
        Algorithm name ('bankers_safety' or 'deadlock_detection').
    n : int
        Number of processes.
    m : int
        Number of resource types.
    workload_type : str
        Workload classification ('safe', 'unsafe', 'deadlocked', 'random').
    mean_time_us : float
        Mean execution time in microseconds (μs).
    median_time_us : float
        Median execution time in microseconds (μs).
    min_time_us : float
        Minimum execution time in microseconds (μs).
    max_time_us : float
        Maximum execution time in microseconds (μs).
    stdev_time_us : float
        Sample standard deviation in microseconds (μs).
    repetitions : int
        Number of timed measurement runs.
    warmup_runs : int
        Number of unmeasured warm-up runs.
    seed : int
        PRNG seed used to generate the workload.
    rho_max : float
        Bottleneck resource pressure metric (max_j sum(Need[i][j]) / Total[j]).
    raw_times_us : tuple[float, ...]
        Tuple of raw execution times across all repetitions (in μs).
    metadata : dict
        Additional metadata (timestamp, host platform, notes).
    """

    algorithm: str
    n: int
    m: int
    workload_type: str
    mean_time_us: float
    median_time_us: float
    min_time_us: float
    max_time_us: float
    stdev_time_us: float
    repetitions: int
    warmup_runs: int
    seed: int
    rho_max: float
    raw_times_us: Tuple[float, ...]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a JSON-serializable dictionary."""
        d = asdict(self)
        d["raw_times_us"] = list(self.raw_times_us)
        return d


# ═══════════════════════════════════════════════════════════════════════
# Statistical Metrics Calculation
# ═══════════════════════════════════════════════════════════════════════


def compute_metrics(times_us: List[float]) -> Dict[str, float]:
    """
    Compute descriptive statistics for a list of execution times in μs.

    Parameters
    ----------
    times_us : list[float]
        List of measured times (must have at least one element).

    Returns
    -------
    dict[str, float]
        Dictionary with keys: 'mean', 'median', 'min', 'max', 'stdev'.
    """
    if not times_us:
        raise BenchmarkError("times_us list must contain at least one measurement.")

    mean_val = statistics.mean(times_us)
    median_val = statistics.median(times_us)
    min_val = min(times_us)
    max_val = max(times_us)
    stdev_val = statistics.stdev(times_us) if len(times_us) > 1 else 0.0

    return {
        "mean": mean_val,
        "median": median_val,
        "min": min_val,
        "max": max_val,
        "stdev": stdev_val,
    }


# ═══════════════════════════════════════════════════════════════════════
# Core Timing Runners
# ═══════════════════════════════════════════════════════════════════════


def time_bankers_safety(
    state: SystemState,
    repetitions: int = 10,
    warmup_runs: int = 2,
) -> List[float]:
    """
    Measure execution time of Banker's safety_check in microseconds (μs).

    Parameters
    ----------
    state : SystemState
        Pre-instantiated system state.
    repetitions : int
        Number of timed executions (>= 1).
    warmup_runs : int
        Number of unmeasured warm-up executions (>= 0).

    Returns
    -------
    list[float]
        Measured execution times in microseconds (μs).
    """
    if repetitions < 1:
        raise BenchmarkError(f"repetitions={repetitions} must be >= 1.")
    if warmup_runs < 0:
        raise BenchmarkError(f"warmup_runs={warmup_runs} must be >= 0.")

    # 1. Warm-up runs (unmeasured)
    for _ in range(warmup_runs):
        safety_check(state)

    # 2. Timed measurement runs
    times_us: List[float] = []
    for _ in range(repetitions):
        t0 = time.perf_counter()
        safety_check(state)
        t1 = time.perf_counter()
        times_us.append((t1 - t0) * 1e6)

    return times_us


def time_deadlock_detection(
    state: SystemState,
    request: List[List[int]],
    repetitions: int = 10,
    warmup_runs: int = 2,
) -> List[float]:
    """
    Measure execution time of detect_deadlock in microseconds (μs).

    Parameters
    ----------
    state : SystemState
        Pre-instantiated system state.
    request : list[list[int]]
        Pre-instantiated Request matrix (shape n × m).
    repetitions : int
        Number of timed executions (>= 1).
    warmup_runs : int
        Number of unmeasured warm-up executions (>= 0).

    Returns
    -------
    list[float]
        Measured execution times in microseconds (μs).
    """
    if repetitions < 1:
        raise BenchmarkError(f"repetitions={repetitions} must be >= 1.")
    if warmup_runs < 0:
        raise BenchmarkError(f"warmup_runs={warmup_runs} must be >= 0.")

    # 1. Warm-up runs (unmeasured)
    for _ in range(warmup_runs):
        detect_deadlock(state, request)

    # 2. Timed measurement runs
    times_us: List[float] = []
    for _ in range(repetitions):
        t0 = time.perf_counter()
        detect_deadlock(state, request)
        t1 = time.perf_counter()
        times_us.append((t1 - t0) * 1e6)

    return times_us


# ═══════════════════════════════════════════════════════════════════════
# High-Level Benchmark Evaluation
# ═══════════════════════════════════════════════════════════════════════


def benchmark_single_workload(
    state: SystemState,
    request: Optional[List[List[int]]] = None,
    workload_type: str = "custom",
    repetitions: int = 10,
    warmup_runs: int = 2,
    seed: int = 42,
    include_bankers: bool = True,
    include_detector: bool = True,
) -> List[BenchmarkResult]:
    """
    Execute benchmark on a single pre-generated workload.

    Parameters
    ----------
    state : SystemState
        The system state to evaluate.
    request : list[list[int]], optional
        Request matrix for deadlock detection. If omitted and include_detector
        is True, a zero request matrix is constructed.
    workload_type : str
        Classification label for this workload.
    repetitions : int
        Number of repetitions per measurement.
    warmup_runs : int
        Number of warm-up runs.
    seed : int
        Seed associated with this workload.
    include_bankers : bool
        Whether to time Banker's safety check.
    include_detector : bool
        Whether to time deadlock detection.

    Returns
    -------
    list[BenchmarkResult]
        BenchmarkResult objects for each evaluated algorithm.
    """
    results: List[BenchmarkResult] = []
    n, m = state.n, state.m
    rho_max = state.max_pressure()

    meta = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    if include_bankers:
        b_times = time_bankers_safety(
            state, repetitions=repetitions, warmup_runs=warmup_runs
        )
        b_stats = compute_metrics(b_times)
        results.append(
            BenchmarkResult(
                algorithm="bankers_safety",
                n=n,
                m=m,
                workload_type=workload_type,
                mean_time_us=b_stats["mean"],
                median_time_us=b_stats["median"],
                min_time_us=b_stats["min"],
                max_time_us=b_stats["max"],
                stdev_time_us=b_stats["stdev"],
                repetitions=repetitions,
                warmup_runs=warmup_runs,
                seed=seed,
                rho_max=rho_max,
                raw_times_us=tuple(b_times),
                metadata=dict(meta),
            )
        )

    if include_detector:
        actual_req = request if request is not None else make_zero_request(n, m)
        d_times = time_deadlock_detection(
            state, actual_req, repetitions=repetitions, warmup_runs=warmup_runs
        )
        d_stats = compute_metrics(d_times)
        results.append(
            BenchmarkResult(
                algorithm="deadlock_detection",
                n=n,
                m=m,
                workload_type=workload_type,
                mean_time_us=d_stats["mean"],
                median_time_us=d_stats["median"],
                min_time_us=d_stats["min"],
                max_time_us=d_stats["max"],
                stdev_time_us=d_stats["stdev"],
                repetitions=repetitions,
                warmup_runs=warmup_runs,
                seed=seed,
                rho_max=rho_max,
                raw_times_us=tuple(d_times),
                metadata=dict(meta),
            )
        )

    return results


def run_scaling_benchmark(
    process_counts: List[int],
    resource_counts: List[int],
    workload_types: Tuple[str, ...] = ("safe", "unsafe", "deadlocked"),
    repetitions: int = 10,
    warmup_runs: int = 2,
    seed: int = 42,
) -> List[BenchmarkResult]:
    """
    Run the multi-dimensional scaling benchmark across n, m, and workload types.

    Parameters
    ----------
    process_counts : list[int]
        List of process counts (e.g. [5, 10, 20, 50]).
    resource_counts : list[int]
        List of resource type counts (e.g. [3, 5, 10]).
    workload_types : tuple[str, ...]
        Types of workloads to evaluate: any of ('safe', 'unsafe', 'deadlocked', 'random').
    repetitions : int
        Measurement repetitions per data point (default: 10).
    warmup_runs : int
        Warm-up runs per data point (default: 2).
    seed : int
        Base PRNG seed.

    Returns
    -------
    list[BenchmarkResult]
        All collected benchmark results.
    """
    if not process_counts:
        raise BenchmarkError("process_counts must not be empty.")
    if not resource_counts:
        raise BenchmarkError("resource_counts must not be empty.")

    all_results: List[BenchmarkResult] = []

    for n in process_counts:
        for m in resource_counts:
            config_seed = seed + n * 1000 + m

            for w_type in workload_types:
                w_seed = config_seed + hash(w_type) % 500

                # Pre-generate workload outside of timing loop
                if w_type == "safe":
                    state = make_safe_state(n, m, total_per_type=max(n * 2, 20), seed=w_seed)
                    req = make_zero_request(n, m)
                elif w_type == "unsafe":
                    state = make_unsafe_state(n, m, total_per_type=max(n, 10), seed=w_seed)
                    req = make_random_request(state, seed=w_seed)
                elif w_type == "deadlocked":
                    state, req = make_deadlocked_workload(n, m, total_per_type=max(n, 10), seed=w_seed)
                elif w_type == "random":
                    state = make_state(n, m, [max(n, 10)] * m, seed=w_seed)
                    req = make_random_request(state, seed=w_seed)
                else:
                    raise BenchmarkError(f"Unknown workload_type: {w_type!r}")

                results = benchmark_single_workload(
                    state=state,
                    request=req,
                    workload_type=w_type,
                    repetitions=repetitions,
                    warmup_runs=warmup_runs,
                    seed=w_seed,
                    include_bankers=True,
                    include_detector=True,
                )
                all_results.extend(results)

    return all_results


# ═══════════════════════════════════════════════════════════════════════
# Operational Overhead Simulation
# ═══════════════════════════════════════════════════════════════════════


def run_operational_overhead_simulation(
    state: SystemState,
    request_stream_length: int = 100,
    detection_sweep_interval: int = 10,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Simulate cumulative operational overhead comparing:
        - Strategy A (Proactive Avoidance): Banker's safety check on every request.
        - Strategy B (Reactive Detection): Grant immediately if Available;
          run deadlock detection periodically every `detection_sweep_interval` requests.

    Parameters
    ----------
    state : SystemState
        Initial system state.
    request_stream_length : int
        Number of dynamic resource requests to process.
    detection_sweep_interval : int
        Frequency of detection algorithm invocation.
    seed : int
        PRNG seed for reproducible request stream.

    Returns
    -------
    dict[str, Any]
        Summary containing cumulative timing, checks performed, and outcomes.
    """
    if request_stream_length < 1:
        raise BenchmarkError("request_stream_length must be >= 1.")
    if detection_sweep_interval < 1:
        raise BenchmarkError("detection_sweep_interval must be >= 1.")

    import random
    rng = random.Random(seed)
    n, m = state.n, state.m

    # Generate synthetic stream of small incremental requests
    # Each request is (process_id, request_vector)
    request_stream: List[Tuple[int, List[int]]] = []
    for _ in range(request_stream_length):
        pid = rng.randint(0, n - 1)
        r_vec = [rng.randint(0, max(1, state.allocation[pid][j])) for j in range(m)]
        request_stream.append((pid, r_vec))

    # --- Strategy A: Proactive Banker's Avoidance ---
    strat_a_time_us = 0.0
    strat_a_checks = 0
    for pid, req_vec in request_stream:
        # Time the safety evaluation on each incoming request
        t0 = time.perf_counter()
        safety_check(state)
        t1 = time.perf_counter()
        strat_a_time_us += (t1 - t0) * 1e6
        strat_a_checks += 1

    # --- Strategy B: Reactive Periodic Detection ---
    strat_b_time_us = 0.0
    strat_b_checks = 0
    curr_req_matrix = [[0] * m for _ in range(n)]

    for step_idx, (pid, req_vec) in enumerate(request_stream, start=1):
        # Update current outstanding request snapshot
        curr_req_matrix[pid] = list(req_vec)

        # Trigger periodic sweep
        if step_idx % detection_sweep_interval == 0:
            t0 = time.perf_counter()
            detect_deadlock(state, curr_req_matrix)
            t1 = time.perf_counter()
            strat_b_time_us += (t1 - t0) * 1e6
            strat_b_checks += 1

    return {
        "n": n,
        "m": m,
        "request_stream_length": request_stream_length,
        "detection_sweep_interval": detection_sweep_interval,
        "strategy_a": {
            "name": "Banker's Avoidance (Per-Request Check)",
            "checks_executed": strat_a_checks,
            "cumulative_time_us": strat_a_time_us,
            "mean_time_per_check_us": strat_a_time_us / max(1, strat_a_checks),
        },
        "strategy_b": {
            "name": "Periodic Detection (Sweep Every K Requests)",
            "checks_executed": strat_b_checks,
            "cumulative_time_us": strat_b_time_us,
            "mean_time_per_check_us": strat_b_time_us / max(1, strat_b_checks),
        },
        "cumulative_overhead_ratio_A_vs_B": (
            strat_a_time_us / strat_b_time_us if strat_b_time_us > 0 else 0.0
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# Export Utilities
# ═══════════════════════════════════════════════════════════════════════


CSV_FIELDNAMES = [
    "algorithm",
    "n",
    "m",
    "workload_type",
    "mean_time_us",
    "median_time_us",
    "min_time_us",
    "max_time_us",
    "stdev_time_us",
    "repetitions",
    "warmup_runs",
    "seed",
    "rho_max",
]


def export_to_csv(results: List[BenchmarkResult], filepath: str) -> None:
    """
    Export benchmark results to a standard CSV file.

    Parameters
    ----------
    results : list[BenchmarkResult]
        List of benchmark result records.
    filepath : str
        Target file path. Parent directories are created automatically.
    """
    if not results:
        raise BenchmarkError("Cannot export empty results list to CSV.")

    dir_path = os.path.dirname(os.path.abspath(filepath))
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for r in results:
            row = {
                "algorithm": r.algorithm,
                "n": r.n,
                "m": r.m,
                "workload_type": r.workload_type,
                "mean_time_us": round(r.mean_time_us, 4),
                "median_time_us": round(r.median_time_us, 4),
                "min_time_us": round(r.min_time_us, 4),
                "max_time_us": round(r.max_time_us, 4),
                "stdev_time_us": round(r.stdev_time_us, 4),
                "repetitions": r.repetitions,
                "warmup_runs": r.warmup_runs,
                "seed": r.seed,
                "rho_max": round(r.rho_max, 4),
            }
            writer.writerow(row)


def export_to_json(
    results: List[BenchmarkResult],
    filepath: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Export benchmark results and complete metadata to a structured JSON file.

    Parameters
    ----------
    results : list[BenchmarkResult]
        List of benchmark result records.
    filepath : str
        Target file path. Parent directories are created automatically.
    extra_metadata : dict, optional
        Additional metadata (e.g. experiment configuration, description).
    """
    if not results:
        raise BenchmarkError("Cannot export empty results list to JSON.")

    dir_path = os.path.dirname(os.path.abspath(filepath))
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    payload = {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "record_count": len(results),
            **(extra_metadata or {}),
        },
        "results": [r.to_dict() for r in results],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
