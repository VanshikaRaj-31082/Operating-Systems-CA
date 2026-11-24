"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/benchmark.py

Benchmarking Engine and Metric Collection for Deadlock Detection Algorithms.

Key Architectural Principles:
1. Strict Timing Isolation:
   - High-precision timing via `time.perf_counter()`.
   - Workload generation, input validation, ground-truth verification, and result
     serialization occur STRICTLY OUTSIDE the timed measurement blocks.
2. Warm-Up Isolation:
   - Configurable untimed warm-up iterations prime CPU instruction caches and runtime buffers.
   - Warm-up timings are completely excluded from statistical metrics.
3. Model/Detector Compatibility Enforcement:
   - Wait-For Graph (WFG) is restricted to single-instance models (Total=1).
   - Incompatible algorithm/model combinations raise IncompatibleDetectorError.
4. Robust Statistics:
   - Computes mean, median, min, max, and sample standard deviation in microseconds (us).
   - Explicitly handles N < 2 cases where sample standard deviation is mathematically undefined.
5. Non-Destructive Storage:
   - Protects against accidental overwrites with explicit overwrite flags and unique naming.
   - Segregates raw measurement logs (JSON) from processed tabular summaries (CSV).
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.models import SystemState
from src.config import EnvironmentMetadata, BenchmarkConfig
from src.detectors.wait_for_graph import detect_wfg_deadlock, WFGResult
from src.detectors.multi_instance_detector import detect_multi_instance_deadlock, MultiInstanceResult


class BenchmarkError(Exception):
    """Base exception for benchmarking framework failures."""
    pass


class IncompatibleDetectorError(BenchmarkError):
    """Raised when an algorithm is invoked on an incompatible resource model."""
    pass


class ResultStorageError(BenchmarkError):
    """Raised when result file persistence fails or violates overwrite policy."""
    pass


@dataclass(frozen=True)
class BenchmarkTimingRecord:
    """
    Complete measurement record for an individual benchmark configuration trial.

    All timing metrics are represented in microseconds (us).
    """
    trial_id: str
    algorithm: str
    resource_model: str
    pattern: str
    n: int
    m: int
    seed: Optional[int]
    warmup_runs: int
    repetitions: int
    raw_timings_us: List[float]
    mean_us: float
    median_us: float
    min_us: float
    max_us: float
    stddev_us: Optional[float]
    is_deadlocked: bool
    deadlocked_count: int
    deadlocked_processes: List[int]
    environment: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Returns a flat dictionary formatted for tabular CSV summaries."""
        return {
            "trial_id": self.trial_id,
            "algorithm": self.algorithm,
            "resource_model": self.resource_model,
            "pattern": self.pattern,
            "n": self.n,
            "m": self.m,
            "seed": self.seed if self.seed is not None else -1,
            "warmup_runs": self.warmup_runs,
            "repetitions": self.repetitions,
            "mean_us": round(self.mean_us, 4),
            "median_us": round(self.median_us, 4),
            "min_us": round(self.min_us, 4),
            "max_us": round(self.max_us, 4),
            "stddev_us": round(self.stddev_us, 4) if self.stddev_us is not None else "",
            "is_deadlocked": self.is_deadlocked,
            "deadlocked_count": self.deadlocked_count,
        }


def compute_timing_statistics(raw_times_sec: List[float]) -> Tuple[float, float, float, float, Optional[float]]:
    """
    Converts timing measurements from seconds to microseconds and computes
    mean, median, min, max, and sample standard deviation.

    Parameters
    ----------
    raw_times_sec : List[float]
        List of elapsed times measured in seconds.

    Returns
    -------
    Tuple[float, float, float, float, Optional[float]]
        (mean_us, median_us, min_us, max_us, stddev_us)
        stddev_us is None if len(raw_times_sec) < 2.
    """
    if not raw_times_sec:
        raise BenchmarkError("Cannot compute statistics on empty measurement list.")

    # Convert to microseconds
    times_us = [t * 1_000_000.0 for t in raw_times_sec]
    n_obs = len(times_us)

    mean_val = sum(times_us) / n_obs

    # Compute median
    sorted_times = sorted(times_us)
    if n_obs % 2 == 1:
        median_val = sorted_times[n_obs // 2]
    else:
        mid = n_obs // 2
        median_val = (sorted_times[mid - 1] + sorted_times[mid]) / 2.0

    min_val = sorted_times[0]
    max_val = sorted_times[-1]

    # Sample standard deviation (Bessel's correction n-1)
    if n_obs < 2:
        # For one measured observation, sample standard deviation is mathematically undefined
        stddev_val = None
    else:
        variance = sum((x - mean_val) ** 2 for x in times_us) / (n_obs - 1)
        stddev_val = math.sqrt(max(0.0, variance))

    return mean_val, median_val, min_val, max_val, stddev_val


def validate_detector_compatibility(algorithm: str, state: SystemState) -> None:
    """
    Enforces theoretical compatibility between detection algorithms and resource models.

    - 'wait_for_graph': Permitted ONLY on single-instance resource models (Total[j] == 1).
    - 'multi_instance': Permitted on all valid models.
    """
    if algorithm == "wait_for_graph":
        if not state.is_single_instance:
            raise IncompatibleDetectorError(
                f"Wait-For Graph detector is mathematically defined only for single-instance models (Total=1). "
                f"Attempted to run on multi-instance state with Total={state.total}."
            )
    elif algorithm == "multi_instance":
        pass
    else:
        raise IncompatibleDetectorError(f"Unknown detection algorithm: '{algorithm}'")


def benchmark_single_trial(
    state: SystemState,
    algorithm: str,
    pattern: str = "custom",
    seed: Optional[int] = None,
    warmup_runs: int = 3,
    repetitions: int = 10,
    expected_is_deadlocked: Optional[bool] = None,
    detector_callable: Optional[Callable[[SystemState], Any]] = None,
    env_metadata: Optional[EnvironmentMetadata] = None,
) -> BenchmarkTimingRecord:
    """
    Executes an isolated, statistically rigorous benchmark trial for a given SystemState.

    Parameters
    ----------
    state : SystemState
        The valid input state.
    algorithm : str
        Algorithm identifier: 'wait_for_graph' or 'multi_instance'.
    pattern : str
        Workload pattern identifier ('acyclic', 'circular', 'random', 'mixed').
    seed : Optional[int]
        Deterministic seed associated with the workload.
    warmup_runs : int
        Number of unmeasured warm-up iterations.
    repetitions : int
        Number of timed measurement iterations (must be >= 1).
    expected_is_deadlocked : Optional[bool]
        Known ground-truth verdict to validate before timing (if known).
    detector_callable : Optional[Callable[[SystemState], Any]]
        Optional override for testing/mocking detector execution.
    env_metadata : Optional[EnvironmentMetadata]
        Host system metadata. Captured automatically if None.

    Returns
    -------
    BenchmarkTimingRecord
        Full measurement record with raw timings and statistical summary.
    """
    if repetitions < 1:
        raise BenchmarkError(f"repetitions must be at least 1, got {repetitions}")
    if warmup_runs < 0:
        raise BenchmarkError(f"warmup_runs cannot be negative, got {warmup_runs}")

    # 1. Compatibility Check (Outside Timed Block)
    validate_detector_compatibility(algorithm, state)

    # 2. Select execution target
    if detector_callable is not None:
        target_fn = detector_callable
    elif algorithm == "wait_for_graph":
        target_fn = detect_wfg_deadlock
    elif algorithm == "multi_instance":
        target_fn = detect_multi_instance_deadlock
    else:
        raise IncompatibleDetectorError(f"Unrecognized algorithm '{algorithm}'")

    # 3. Correctness Validation (Outside Timed Block)
    # Perform one initial execution to extract results and verify ground truth
    initial_res = target_fn(state)

    if isinstance(initial_res, WFGResult):
        is_deadlocked = initial_res.is_deadlocked
        deadlocked_processes = list(initial_res.deadlocked_processes)
    elif isinstance(initial_res, MultiInstanceResult):
        is_deadlocked = initial_res.is_deadlocked
        deadlocked_processes = list(initial_res.deadlocked_processes)
    else:
        # Support mock results with expected attributes
        is_deadlocked = getattr(initial_res, "is_deadlocked", False)
        deadlocked_processes = getattr(initial_res, "deadlocked_processes", [])

    if expected_is_deadlocked is not None:
        if is_deadlocked != expected_is_deadlocked:
            raise BenchmarkError(
                f"Ground-truth validation failed before timing: expected is_deadlocked={expected_is_deadlocked}, "
                f"got {is_deadlocked}"
            )

    # 4. Untimed Warm-Up Iterations (Excluded from statistics)
    for _ in range(warmup_runs):
        target_fn(state)

    # 5. Strictly Timed Repetitions
    raw_measurements_sec: List[float] = []
    for _ in range(repetitions):
        t_start = time.perf_counter()
        target_fn(state)
        t_end = time.perf_counter()
        raw_measurements_sec.append(t_end - t_start)

    # 6. Statistical Computation
    mean_us, median_us, min_us, max_us, stddev_us = compute_timing_statistics(raw_measurements_sec)

    if env_metadata is None:
        env_metadata = EnvironmentMetadata.capture()

    resource_model = "single_instance" if state.is_single_instance else "multi_instance"
    trial_id = f"{algorithm}_{pattern}_n{state.n}_m{state.m}_s{seed if seed is not None else 0}"

    raw_us_list = [t * 1_000_000.0 for t in raw_measurements_sec]

    return BenchmarkTimingRecord(
        trial_id=trial_id,
        algorithm=algorithm,
        resource_model=resource_model,
        pattern=pattern,
        n=state.n,
        m=state.m,
        seed=seed,
        warmup_runs=warmup_runs,
        repetitions=repetitions,
        raw_timings_us=raw_us_list,
        mean_us=mean_us,
        median_us=median_us,
        min_us=min_us,
        max_us=max_us,
        stddev_us=stddev_us,
        is_deadlocked=is_deadlocked,
        deadlocked_count=len(deadlocked_processes),
        deadlocked_processes=deadlocked_processes,
        environment=env_metadata.to_dict(),
    )


# ─────────────────────────────────────────────────────────────────────
# Result Persistence & File Output
# ─────────────────────────────────────────────────────────────────────

def save_raw_results(
    records: List[BenchmarkTimingRecord],
    filepath: Union[str, Path],
    overwrite: bool = False
) -> None:
    """
    Saves raw individual benchmark records and environment metadata as structured JSON.

    Parameters
    ----------
    records : List[BenchmarkTimingRecord]
        List of timing records to persist.
    filepath : Union[str, Path]
        Target JSON filepath.
    overwrite : bool, default=False
        If False, raises ResultStorageError if target file already exists.
    """
    path = Path(filepath)
    if path.exists() and not overwrite:
        raise ResultStorageError(f"Target raw results file '{path}' already exists and overwrite=False.")

    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "metadata": {
            "record_count": len(records),
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "records": [r.to_dict() for r in records],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_processed_summary_csv(
    records: List[BenchmarkTimingRecord],
    filepath: Union[str, Path],
    overwrite: bool = False
) -> None:
    """
    Saves aggregated benchmark statistics to a CSV table with standard headers.

    Parameters
    ----------
    records : List[BenchmarkTimingRecord]
        List of timing records to summarize.
    filepath : Union[str, Path]
        Target CSV filepath.
    overwrite : bool, default=False
        If False, raises ResultStorageError if target file already exists.
    """
    path = Path(filepath)
    if path.exists() and not overwrite:
        raise ResultStorageError(f"Target processed CSV file '{path}' already exists and overwrite=False.")

    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        return

    fieldnames = list(records[0].to_summary_dict().keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_summary_dict())
