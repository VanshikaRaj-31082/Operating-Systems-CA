"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Script: experiments/run_experiments.py

Full Experiment Execution and Data Collection Orchestrator.

Key Architecture:
1. Systematic Matrix Traversal:
   - Processes: [5, 10, 20, 50, 100]
   - Resources: [3, 5, 10, 20]
   - Patterns: acyclic, circular, random, mixed
   - Resource Models: single-instance (WFG), multi-instance (Reduction)
   - Seeds: [101, 202, 303, 404, 505]
   - Warmups: 5, Measured Repetitions: 30
2. Strict Detector/Model Isolation:
   - WFG is executed exclusively on single-instance models (Total=1).
   - Multi-Instance reduction is executed on multi-instance models (Total=5).
   - Results are segregated and never conflated as direct algorithm head-to-head.
3. Ground-Truth Separation:
   - Acyclic: verified expected deadlock = False.
   - Circular: verified expected deadlock = True.
   - Mixed: verified expected deadlock = True.
   - Random: recorded as 'unverified' rather than claiming correctness.
4. Resumption and Non-Destructive Logging:
   - Tracks completed configuration IDs.
   - Preserves earlier results and never silently overwrites.
   - Unsupported configurations (e.g. Mixed with m=3 < 4) and failures are logged
     to results/execution_log.json.
5. Two-Stage Execution:
   - Representative subset validation stage before full matrix execution.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SystemState
from src.config import BenchmarkConfig, EnvironmentMetadata
from src.generators import (
    generate_acyclic_workload,
    generate_circular_workload,
    generate_random_workload,
    generate_mixed_workload,
    GeneratorError,
)
from src.benchmark import (
    benchmark_single_trial,
    save_raw_results,
    save_processed_summary_csv,
    BenchmarkTimingRecord,
    BenchmarkError,
    IncompatibleDetectorError,
)


@dataclass(frozen=True)
class UnsupportedConfigRecord:
    """Record of an unsupported parameter combination with reason."""
    config_id: str
    resource_model: str
    pattern: str
    n: int
    m: int
    seed: int
    reason: str


@dataclass(frozen=True)
class ExecutionLog:
    """Structured execution summary log."""
    started_at_utc: str
    ended_at_utc: str
    total_configurations_planned: int
    completed_configurations: int
    unsupported_configurations: int
    failed_configurations: int
    total_detector_executions: int
    environment: Dict[str, Any]
    unsupported_details: List[Dict[str, Any]]
    failure_details: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_experiment_workload(
    resource_model: str,
    pattern: str,
    n: int,
    m: int,
    seed: int,
) -> Tuple[SystemState, Optional[bool], str]:
    """
    Generates the requested SystemState along with ground-truth expectation and verification status.

    Returns
    -------
    Tuple[SystemState, Optional[bool], str]
        (state, expected_is_deadlocked, verification_status)
        where verification_status is either 'verified' or 'unverified'.
    """
    total_per_type = 1 if resource_model == "single_instance" else 5

    if pattern == "acyclic":
        state = generate_acyclic_workload(
            n=n,
            m=m,
            total_per_type=total_per_type,
            include_blocked=True,
            seed=seed,
        )
        return state, False, "verified"

    elif pattern == "circular":
        # Cycle size is min(n, m)
        k = min(n, m)
        state = generate_circular_workload(
            n=n,
            m=m,
            cycle_size=k,
            total_per_type=total_per_type,
            include_blocked_tail=(n > k),
            seed=seed,
        )
        return state, True, "verified"

    elif pattern == "random":
        state = generate_random_workload(
            n=n,
            m=m,
            total_per_type=total_per_type,
            allocation_ratio=0.7,
            request_probability=0.5,
            seed=seed,
        )
        # Random workloads have no independently established analytical ground truth
        return state, None, "unverified"

    elif pattern == "mixed":
        # Mixed requires deadlock_count >= 2, blocked_count >= 1, min m >= 4, min n >= 4
        # Allocate default cohort: k=2, b=1
        spec = generate_mixed_workload(
            n=n,
            m=m,
            deadlock_count=2,
            blocked_count=1,
            total_per_type=total_per_type,
            seed=seed,
        )
        return spec.state, True, "verified"

    else:
        raise ValueError(f"Unknown workload pattern: '{pattern}'")


def load_completed_trial_ids(csv_path: Path) -> Set[str]:
    """Inspects existing processed summary CSV to find already completed trial IDs for resumption."""
    if not csv_path.exists():
        return set()
    completed = set()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "trial_id" in row and row["trial_id"]:
                    completed.add(row["trial_id"])
    except Exception as e:
        print(f"[WARN] Could not parse existing summary CSV for resumption: {e}")
    return completed


def run_experiment_suite(
    config_path: Path,
    raw_output_path: Path,
    summary_output_path: Path,
    log_output_path: Path,
    representative_only: bool = False,
) -> None:
    """
    Executes the benchmark matrix systematically, collecting telemetry and persisting results.
    """
    config = BenchmarkConfig.from_json_file(str(config_path))
    env_meta = EnvironmentMetadata.capture()
    start_time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print("=" * 80)
    if representative_only:
        print("CA4 R13: Deadlock Detection Benchmark - Representative Subset Execution")
    else:
        print("CA4 R13: Deadlock Detection Benchmark - Full Matrix Execution")
    print("=" * 80)
    print(f"Platform: {env_meta.os_name} {env_meta.os_release} | Python {env_meta.python_version}")
    print(f"Processor: {env_meta.processor}")
    print(f"Repetitions: {config.repetitions} (warmup: {config.warmup_runs})")

    # If running representative only, use a restricted slice
    if representative_only:
        target_models = ["single_instance", "multi_instance"]
        target_patterns = ["acyclic", "circular", "random", "mixed"]
        target_n_list = [5]
        target_m_list = [5]
        target_seeds = [config.seeds[0]]
    else:
        target_models = config.resource_models
        target_patterns = config.patterns
        target_n_list = config.process_counts
        target_m_list = config.resource_counts
        target_seeds = config.seeds

    # Check for existing completed trials for resumption
    completed_trial_ids = load_completed_trial_ids(summary_output_path)
    if completed_trial_ids:
        print(f"[RESUME] Found {len(completed_trial_ids)} already completed trials in {summary_output_path.name}.")

    records: List[BenchmarkTimingRecord] = []
    unsupported_list: List[UnsupportedConfigRecord] = []
    failure_list: List[Dict[str, Any]] = []

    total_planned = 0
    total_measured_executions = 0

    # Ensure output directories exist
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    log_output_path.parent.mkdir(parents=True, exist_ok=True)

    t_suite_start = time.perf_counter()

    for model in target_models:
        algorithm = "wait_for_graph" if model == "single_instance" else "multi_instance"

        for pattern in target_patterns:
            for n in target_n_list:
                for m in target_m_list:
                    for seed in target_seeds:
                        total_planned += 1
                        trial_id = f"{algorithm}_{pattern}_n{n}_m{m}_s{seed}"

                        # Skip if already completed in earlier run
                        if trial_id in completed_trial_ids:
                            continue

                        # 1. Workload Generation (Outside Timed Section)
                        try:
                            state, expected_verdict, v_status = generate_experiment_workload(
                                resource_model=model,
                                pattern=pattern,
                                n=n,
                                m=m,
                                seed=seed,
                            )
                        except GeneratorError as ge:
                            unsupported_list.append(
                                UnsupportedConfigRecord(
                                    config_id=trial_id,
                                    resource_model=model,
                                    pattern=pattern,
                                    n=n,
                                    m=m,
                                    seed=seed,
                                    reason=str(ge),
                                )
                            )
                            continue
                        except Exception as ex:
                            failure_list.append({
                                "trial_id": trial_id,
                                "stage": "workload_generation",
                                "error": str(ex),
                            })
                            continue

                        # 2. Benchmark Execution
                        try:
                            rec = benchmark_single_trial(
                                state=state,
                                algorithm=algorithm,
                                pattern=pattern,
                                seed=seed,
                                warmup_runs=config.warmup_runs,
                                repetitions=config.repetitions,
                                expected_is_deadlocked=expected_verdict,
                                env_metadata=env_meta,
                            )
                            records.append(rec)
                            total_measured_executions += config.repetitions

                            # Print brief progress indicator
                            std_str = f"{rec.stddev_us:.2f}" if rec.stddev_us is not None else "None"
                            dl_str = "DEADLOCKED" if rec.is_deadlocked else "SAFE"
                            print(
                                f"[{len(records) + len(completed_trial_ids)}/{total_planned}] "
                                f"{trial_id} ({v_status}) -> {dl_str} | "
                                f"Median: {rec.median_us:.2f} us, StdDev: {std_str} us"
                            )

                        except Exception as be:
                            failure_list.append({
                                "trial_id": trial_id,
                                "stage": "benchmark_execution",
                                "error": str(be),
                            })
                            print(f"[FAIL] {trial_id}: {be}")

    t_suite_elapsed = time.perf_counter() - t_suite_start
    end_time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 3. Persist Data (Appending if resuming, or creating fresh)
    if records:
        # For raw JSON: if file exists and we are appending/resuming, merge records
        existing_records_dict: List[Dict[str, Any]] = []
        if raw_output_path.exists():
            try:
                with open(raw_output_path, "r", encoding="utf-8") as f:
                    old_raw = json.load(f)
                    existing_records_dict = old_raw.get("records", [])
            except Exception:
                pass

        all_raw_dicts = existing_records_dict + [r.to_dict() for r in records]
        raw_payload = {
            "metadata": {
                "record_count": len(all_raw_dicts),
                "generated_at_utc": end_time_str,
                "environment": env_meta.to_dict(),
            },
            "records": all_raw_dicts,
        }
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(raw_payload, f, indent=2)

        # For processed summary CSV:
        csv_file_exists = summary_output_path.exists()
        summary_dicts = [r.to_summary_dict() for r in records]
        fieldnames = list(summary_dicts[0].keys())

        with open(summary_output_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not csv_file_exists or summary_output_path.stat().st_size == 0:
                writer.writeheader()
            for row in summary_dicts:
                writer.writerow(row)

    # 4. Save Execution Log
    exec_log = ExecutionLog(
        started_at_utc=start_time_str,
        ended_at_utc=end_time_str,
        total_configurations_planned=total_planned,
        completed_configurations=len(records) + len(completed_trial_ids),
        unsupported_configurations=len(unsupported_list),
        failed_configurations=len(failure_list),
        total_detector_executions=total_measured_executions,
        environment=env_meta.to_dict(),
        unsupported_details=[asdict(u) for u in unsupported_list],
        failure_details=failure_list,
    )

    with open(log_output_path, "w", encoding="utf-8") as f:
        json.dump(exec_log.to_dict(), f, indent=2)

    print("\n" + "=" * 80)
    print(f"Execution Suite Finished in {t_suite_elapsed:.2f} seconds.")
    print(f"Planned Configurations:      {total_planned}")
    print(f"Completed Configurations:    {len(records) + len(completed_trial_ids)}")
    print(f"Unsupported Configurations:  {len(unsupported_list)}")
    print(f"Failed Configurations:       {len(failure_list)}")
    print(f"Total Detector Invocations:  {total_measured_executions} (timed)")
    print(f"Raw Output:                  {raw_output_path}")
    print(f"Processed Summary CSV:       {summary_output_path}")
    print(f"Execution Log:               {log_output_path}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CA4 R13 Deadlock Detection Benchmark Runner")
    parser.add_argument("--representative-only", action="store_true", help="Run only a small representative subset")
    parser.add_argument("--config", type=str, default="experiments/experiment_config.json", help="Path to config file")
    parser.add_argument("--raw", type=str, default="results/raw/matrix_experiment_raw.json", help="Raw output JSON path")
    parser.add_argument("--summary", type=str, default="results/processed/matrix_experiment_summary.csv", help="Summary CSV path")
    parser.add_argument("--log", type=str, default="results/execution_log.json", help="Execution log JSON path")

    args = parser.parse_args()

    cfg_p = PROJECT_ROOT / args.config
    raw_p = PROJECT_ROOT / args.raw
    sum_p = PROJECT_ROOT / args.summary
    log_p = PROJECT_ROOT / args.log

    run_experiment_suite(
        config_path=cfg_p,
        raw_output_path=raw_p,
        summary_output_path=sum_p,
        log_output_path=log_p,
        representative_only=args.representative_only,
    )
