"""
Master Linux Concurrency Failure & Lock Contention Investigation Runner.
Implements CA5 Official Challenge L38, integrating L10, L16, L17, and L25.
Follows the 9-Step Engineering Framework:
Observe -> Formulate -> Instrument -> Experiment -> Control -> Analyze -> Engineer -> Validate -> Defend
Produces verifiable JSON raw data, processed CSV tables, and detailed execution logs.
"""

import csv
import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.environment import LinuxEnvironment
from src.proc_explorer import ProcExplorer
from src.workloads.deadlock_scenario import run_deadlock_trial
from src.workloads.lock_contention import run_contention_trial
from src.workloads.race_condition import run_race_trial


def compute_stats(values: List[float]) -> Dict[str, Optional[float]]:
    """Computes mean, median, min, max, and sample standard deviation."""
    if not values:
        return {"mean": None, "median": None, "min": None, "max": None, "stddev": None}
    n = len(values)
    mean_val = statistics.fmean(values)
    median_val = statistics.median(values)
    min_val = min(values)
    max_val = max(values)
    stddev_val = statistics.stdev(values) if n > 1 else None
    return {
        "mean": mean_val,
        "median": median_val,
        "min": min_val,
        "max": max_val,
        "stddev": stddev_val,
    }


class InvestigationRunner:
    """Orchestrates the complete CA5 experimental matrix and evidence collection."""

    def __init__(self, config_path: str = "config/experiment_config.json", base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            # Locate CA5 root directory relative to this file
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            self.base_dir = os.path.abspath(os.path.join(current_file_dir, ".."))
        else:
            self.base_dir = os.path.abspath(base_dir)

        if os.path.isabs(config_path):
            self.config_path = config_path
        else:
            self.config_path = os.path.join(self.base_dir, config_path)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.env = LinuxEnvironment()
        self.explorer = ProcExplorer()

        self.raw_dir = os.path.join(self.base_dir, self.config["output_paths"]["raw_dir"])
        self.processed_dir = os.path.join(self.base_dir, self.config["output_paths"]["processed_dir"])
        self.logs_dir = os.path.join(self.base_dir, self.config["output_paths"]["logs_dir"])
        self.figures_dir = os.path.join(self.base_dir, self.config["output_paths"]["figures_dir"])

        for d in [self.raw_dir, self.processed_dir, self.logs_dir, self.figures_dir]:
            os.makedirs(d, exist_ok=True)

    def run_all_experiments(self) -> Dict[str, Any]:
        """Executes all three investigation phases and serializes results."""
        started_at = datetime.now(timezone.utc).isoformat()
        env_profile = self.env.collect_full_profile()

        raw_results: Dict[str, Any] = {
            "metadata": {
                "project": self.config["project"],
                "primary_challenge": self.config["challenge_id"],
                "challenge_title": self.config["challenge_title"],
                "started_at_utc": started_at,
                "environment": env_profile,
            },
            "race_condition": [],
            "lock_contention": [],
            "deadlock_investigation": [],
        }

        # ---------------------------------------------------------
        # Experiment 1: Race Condition (L10)
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PHASE 1: Race Condition & Correction Experiment (L10)")
        print("=======================================================")
        rc_cfg = self.config["workload_parameters"]["race_condition"]
        threads = rc_cfg["thread_counts"]
        ops = rc_cfg["increments_per_thread"]
        reps = rc_cfg["repetitions"]

        for mode in rc_cfg["modes"]:
            sync_flag = (mode == "mutex_synchronized")
            for t_count in threads:
                for rep in range(1, reps + 1):
                    trial_res = run_race_trial(thread_count=t_count, ops_per_thread=ops, synchronized=sync_flag)
                    trial_record = {
                        "mode": mode,
                        "thread_count": t_count,
                        "ops_per_thread": ops,
                        "repetition": rep,
                        **trial_res
                    }
                    raw_results["race_condition"].append(trial_record)
                print(f"  [Race] Mode: {mode:<20} Threads: {t_count:<2} Completed {reps} reps.")

        # ---------------------------------------------------------
        # Experiment 2: Lock Contention & Context Switches (L16)
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PHASE 2: Lock Contention & Context Switches (L16)")
        print("=======================================================")
        lc_cfg = self.config["workload_parameters"]["lock_contention"]
        lc_threads = lc_cfg["thread_counts"]
        total_ops = lc_cfg["total_operations"]
        lc_reps = lc_cfg["repetitions"]

        for strat in lc_cfg["strategies"]:
            chunk_size = 10 if strat == "chunked_mutex" else 1
            for t_count in lc_threads:
                for rep in range(1, lc_reps + 1):
                    trial_res = run_contention_trial(
                        thread_count=t_count,
                        total_ops=total_ops,
                        strategy=strat,
                        chunk_size=chunk_size,
                        explorer=self.explorer
                    )
                    trial_record = {
                        "strategy": strat,
                        "thread_count": t_count,
                        "chunk_size": chunk_size,
                        "repetition": rep,
                        **trial_res
                    }
                    raw_results["lock_contention"].append(trial_record)
                print(f"  [Contention] Strategy: {strat:<20} Threads: {t_count:<2} Completed {lc_reps} reps.")

        # ---------------------------------------------------------
        # Experiment 3: Deadlock Demonstration & Recovery (L17)
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PHASE 3: Deadlock Demonstration & Recovery (L17)")
        print("=======================================================")
        dl_cfg = self.config["workload_parameters"]["deadlock_investigation"]
        dl_reps = dl_cfg["repetitions"]
        watchdog_to = dl_cfg["watchdog_timeout_sec"]

        for scenario in dl_cfg["scenarios"]:
            for rep in range(1, dl_reps + 1):
                trial_res = run_deadlock_trial(
                    scenario=scenario,
                    watchdog_timeout_s=watchdog_to,
                    ops=100,
                    explorer=self.explorer
                )
                trial_record = {
                    "scenario": scenario,
                    "repetition": rep,
                    **trial_res
                }
                raw_results["deadlock_investigation"].append(trial_record)
            print(f"  [Deadlock] Scenario: {scenario:<38} Completed {dl_reps} reps.")

        ended_at = datetime.now(timezone.utc).isoformat()
        raw_results["metadata"]["ended_at_utc"] = ended_at

        # Save Raw JSON
        raw_path = os.path.join(self.raw_dir, "concurrency_investigation_raw.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_results, f, indent=2)
        print(f"\n[Artifact] Raw measurements saved to: {raw_path}")

        # Process and Save CSVs
        self._process_and_save_summaries(raw_results)

        # Save Execution Log
        log_path = os.path.join(self.logs_dir, "execution_log.json")
        log_data = {
            "execution_status": "completed_successfully",
            "started_at_utc": started_at,
            "ended_at_utc": ended_at,
            "total_race_trials": len(raw_results["race_condition"]),
            "total_contention_trials": len(raw_results["lock_contention"]),
            "total_deadlock_trials": len(raw_results["deadlock_investigation"]),
            "total_experimental_runs": (
                len(raw_results["race_condition"])
                + len(raw_results["lock_contention"])
                + len(raw_results["deadlock_investigation"])
            ),
            "environment_summary": {
                "os": env_profile["os_release"].get("PRETTY_NAME", platform.system()),
                "kernel": env_profile["kernel"].get("release", platform.release()),
                "logical_cpus": env_profile["cpu"].get("logical_cores", os.cpu_count()),
                "python": env_profile["kernel"].get("python_version", platform.python_version()),
            }
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)
        print(f"[Artifact] Execution log saved to: {log_path}")

        return raw_results

    def _process_and_save_summaries(self, raw_data: Dict[str, Any]) -> None:
        """Processes raw trials into grouped statistical summaries and writes CSVs."""
        # 1. Race Condition Summary
        rc_records = raw_data["race_condition"]
        rc_groups: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
        for r in rc_records:
            key = (r["mode"], r["thread_count"])
            rc_groups.setdefault(key, []).append(r)

        rc_summary_path = os.path.join(self.processed_dir, "race_condition_summary.csv")
        with open(rc_summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "mode", "thread_count", "repetition_count",
                "mean_duration_s", "std_duration_s",
                "mean_throughput_ops_sec",
                "mean_discrepancy", "max_discrepancy",
                "mean_relative_error_pct"
            ])
            for (mode, tc), records in sorted(rc_groups.items()):
                durations = [x["duration_s"] for x in records]
                throughputs = [x["throughput_ops_sec"] for x in records]
                discrepancies = [float(x["discrepancy"]) for x in records]
                errors = [x["relative_error"] * 100.0 for x in records]

                d_stats = compute_stats(durations)
                t_stats = compute_stats(throughputs)
                disc_stats = compute_stats(discrepancies)
                err_stats = compute_stats(errors)

                writer.writerow([
                    mode, tc, len(records),
                    f"{d_stats['mean']:.6f}" if d_stats['mean'] is not None else "",
                    f"{d_stats['stddev']:.6f}" if d_stats['stddev'] is not None else "",
                    f"{t_stats['mean']:.2f}" if t_stats['mean'] is not None else "",
                    f"{disc_stats['mean']:.1f}" if disc_stats['mean'] is not None else "",
                    f"{disc_stats['max']:.1f}" if disc_stats['max'] is not None else "",
                    f"{err_stats['mean']:.4f}" if err_stats['mean'] is not None else "",
                ])
        print(f"[Artifact] Processed CSV saved to: {rc_summary_path}")

        # 2. Lock Contention Summary
        lc_records = raw_data["lock_contention"]
        lc_groups: Dict[Tuple[str, int, int], List[Dict[str, Any]]] = {}
        for r in lc_records:
            key = (r["strategy"], r["thread_count"], r["chunk_size"])
            lc_groups.setdefault(key, []).append(r)

        lc_summary_path = os.path.join(self.processed_dir, "lock_contention_summary.csv")
        with open(lc_summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "strategy", "thread_count", "chunk_size", "repetition_count",
                "mean_duration_s", "std_duration_s",
                "mean_throughput_ops_sec", "std_throughput_ops_sec",
                "mean_voluntary_ctxt_switches", "mean_nonvoluntary_ctxt_switches",
                "mean_total_ctxt_switches"
            ])
            for (strat, tc, cs), records in sorted(lc_groups.items()):
                durations = [x["duration_s"] for x in records]
                throughputs = [x["throughput_ops_sec"] for x in records]
                vols = [float(x["voluntary_ctxt_switches"]) for x in records]
                nonvols = [float(x["nonvoluntary_ctxt_switches"]) for x in records]
                totals = [float(x["total_ctxt_switches"]) for x in records]

                d_stats = compute_stats(durations)
                t_stats = compute_stats(throughputs)
                v_stats = compute_stats(vols)
                nv_stats = compute_stats(nonvols)
                tot_stats = compute_stats(totals)

                writer.writerow([
                    strat, tc, cs, len(records),
                    f"{d_stats['mean']:.6f}" if d_stats['mean'] is not None else "",
                    f"{d_stats['stddev']:.6f}" if d_stats['stddev'] is not None else "",
                    f"{t_stats['mean']:.2f}" if t_stats['mean'] is not None else "",
                    f"{t_stats['stddev']:.2f}" if t_stats['stddev'] is not None else "",
                    f"{v_stats['mean']:.1f}" if v_stats['mean'] is not None else "",
                    f"{nv_stats['mean']:.1f}" if nv_stats['mean'] is not None else "",
                    f"{tot_stats['mean']:.1f}" if tot_stats['mean'] is not None else "",
                ])
        print(f"[Artifact] Processed CSV saved to: {lc_summary_path}")

        # 3. Deadlock Investigation Summary
        dl_records = raw_data["deadlock_investigation"]
        dl_groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in dl_records:
            dl_groups.setdefault(r["scenario"], []).append(r)

        dl_summary_path = os.path.join(self.processed_dir, "deadlock_investigation_summary.csv")
        with open(dl_summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "scenario", "repetition_count", "deadlock_rate_pct",
                "mean_execution_time_s", "std_execution_time_s",
                "mean_ops_completed", "mean_retries_count"
            ])
            for scen, records in sorted(dl_groups.items()):
                deadlocks = [1.0 if x["deadlock_observed"] else 0.0 for x in records]
                times = [x["execution_time_s"] for x in records]
                ops = [float(x.get("operations_completed", 0)) for x in records]
                retries = [float(x.get("retries_count", 0)) for x in records]

                d_rate = (sum(deadlocks) / len(deadlocks)) * 100.0
                t_stats = compute_stats(times)
                op_stats = compute_stats(ops)
                ret_stats = compute_stats(retries)

                writer.writerow([
                    scen, len(records), f"{d_rate:.1f}",
                    f"{t_stats['mean']:.6f}" if t_stats['mean'] is not None else "",
                    f"{t_stats['stddev']:.6f}" if t_stats['stddev'] is not None else "",
                    f"{op_stats['mean']:.1f}" if op_stats['mean'] is not None else "",
                    f"{ret_stats['mean']:.1f}" if ret_stats['mean'] is not None else "",
                ])
        print(f"[Artifact] Processed CSV saved to: {dl_summary_path}")


if __name__ == "__main__":
    runner = InvestigationRunner()
    runner.run_all_experiments()
