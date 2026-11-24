"""
Unit Tests for Benchmarking Framework and Metric Collection (src/benchmark.py).
"""

import sys
import tempfile
import os
import json
import csv
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import SystemState
from src.config import BenchmarkConfig, EnvironmentMetadata
from src.benchmark import (
    BenchmarkError,
    IncompatibleDetectorError,
    ResultStorageError,
    BenchmarkTimingRecord,
    compute_timing_statistics,
    validate_detector_compatibility,
    benchmark_single_trial,
    save_raw_results,
    save_processed_summary_csv,
)
from src.detectors.wait_for_graph import WFGResult
from src.detectors.multi_instance_detector import MultiInstanceResult


class TestBenchmarkingEngine(unittest.TestCase):
    """Test suite covering timing metrics, warmups, compatibility, and result persistence."""

    def setUp(self):
        # Sample single-instance state (P0 <-> P1 cycle)
        self.single_state = SystemState(
            total=[1, 1],
            allocation=[[1, 0], [0, 1]],
            request=[[0, 1], [1, 0]],
            available=[0, 0],
        )
        # Sample multi-instance state
        self.multi_state = SystemState(
            total=[3, 3],
            allocation=[[1, 1], [1, 1]],
            request=[[1, 0], [0, 1]],
            available=[1, 1],
        )

    def test_compute_timing_statistics_accuracy(self):
        """Test statistical computations (mean, median, min, max, sample stddev)."""
        # 3 observations in seconds: 1ms, 2ms, 3ms
        raw_seconds = [0.001, 0.002, 0.003]
        mean_us, median_us, min_us, max_us, stddev_us = compute_timing_statistics(raw_seconds)

        self.assertAlmostEqual(mean_us, 2000.0, places=4)
        self.assertAlmostEqual(median_us, 2000.0, places=4)
        self.assertAlmostEqual(min_us, 1000.0, places=4)
        self.assertAlmostEqual(max_us, 3000.0, places=4)
        # Sample standard deviation of [1000, 2000, 3000] with N=3 is 1000.0
        self.assertAlmostEqual(stddev_us, 1000.0, places=4)

    def test_compute_timing_statistics_even_median(self):
        """Test median computation when observation count is even."""
        raw_seconds = [0.001, 0.002, 0.004, 0.005]  # [1000, 2000, 4000, 5000] us
        mean_us, median_us, _, _, _ = compute_timing_statistics(raw_seconds)
        self.assertAlmostEqual(mean_us, 3000.0, places=4)
        # Median is average of 2000 and 4000 = 3000
        self.assertAlmostEqual(median_us, 3000.0, places=4)

    def test_single_observation_sample_stddev_handling(self):
        """
        CRITICAL TEST: Verify that N=1 observation handles sample standard deviation
        gracefully (returns None) without raising ZeroDivisionError.
        """
        single_obs = [0.0025]
        mean_us, median_us, min_us, max_us, stddev_us = compute_timing_statistics(single_obs)

        self.assertAlmostEqual(mean_us, 2500.0, places=4)
        self.assertAlmostEqual(median_us, 2500.0, places=4)
        self.assertAlmostEqual(min_us, 2500.0, places=4)
        self.assertAlmostEqual(max_us, 2500.0, places=4)
        self.assertIsNone(stddev_us, "Sample stddev for N=1 must be None")

    def test_single_observation_serialization(self):
        """Verify that N=1 observation serializes stddev as None/null in JSON and empty string in CSV."""
        rec = benchmark_single_trial(
            state=self.single_state,
            algorithm="wait_for_graph",
            pattern="circular",
            seed=42,
            warmup_runs=0,
            repetitions=1,
        )
        self.assertIsNone(rec.stddev_us)
        summary = rec.to_summary_dict()
        self.assertEqual(summary["stddev_us"], "")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test_n1_raw.json"
            csv_path = Path(tmpdir) / "test_n1_processed.csv"

            save_raw_results([rec], json_path)
            save_processed_summary_csv([rec], csv_path)

            with open(json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self.assertIsNone(raw_data["records"][0]["stddev_us"])

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                row = next(reader)
            self.assertEqual(row["stddev_us"], "")

    def test_empty_timing_list_raises_error(self):
        """Test that empty measurement list raises BenchmarkError."""
        with self.assertRaises(BenchmarkError):
            compute_timing_statistics([])

    def test_warmup_runs_excluded_from_measured_repetitions(self):
        """
        Verify that warmup iterations execute to prime caches, but only
        measured repetitions are recorded in raw timings.
        """
        call_count = [0]

        def mock_detector(state: SystemState):
            call_count[0] += 1
            return WFGResult(
                is_deadlocked=True,
                deadlocked_processes=[0, 1],
                cycles=[[0, 1]],
                blocked_processes=[],
                adjacency_list={},
                edge_count=2,
                is_single_instance=True,
            )

        warmup_runs = 4
        repetitions = 6

        rec = benchmark_single_trial(
            state=self.single_state,
            algorithm="wait_for_graph",
            pattern="circular",
            warmup_runs=warmup_runs,
            repetitions=repetitions,
            detector_callable=mock_detector,
        )

        # Total calls: 1 (pre-validation) + 4 (warmups) + 6 (repetitions) = 11
        self.assertEqual(call_count[0], 1 + warmup_runs + repetitions)
        # Exactly 6 measured timings stored
        self.assertEqual(len(rec.raw_timings_us), repetitions)
        self.assertEqual(rec.warmup_runs, warmup_runs)
        self.assertEqual(rec.repetitions, repetitions)

    def test_detector_model_compatibility_enforcement(self):
        """
        Verify that incompatible combinations (e.g. WFG on multi-instance model)
        are blocked with an explicit IncompatibleDetectorError.
        """
        # Multi-instance state with Total = [3, 3] must fail with WFG detector
        with self.assertRaises(IncompatibleDetectorError):
            validate_detector_compatibility("wait_for_graph", self.multi_state)

        with self.assertRaises(IncompatibleDetectorError):
            benchmark_single_trial(
                state=self.multi_state,
                algorithm="wait_for_graph",
            )

        # Single-instance state must succeed with WFG
        validate_detector_compatibility("wait_for_graph", self.single_state)

        # Multi-instance detector is compatible with both
        validate_detector_compatibility("multi_instance", self.single_state)
        validate_detector_compatibility("multi_instance", self.multi_state)

        # Invalid algorithm name
        with self.assertRaises(IncompatibleDetectorError):
            validate_detector_compatibility("invalid_algo", self.single_state)

    def test_correctness_validation_before_timing(self):
        """Test that expected ground-truth checks are verified outside timed blocks."""
        # single_state is deadlocked. Expecting False must raise BenchmarkError
        with self.assertRaises(BenchmarkError):
            benchmark_single_trial(
                state=self.single_state,
                algorithm="wait_for_graph",
                expected_is_deadlocked=False,  # Mismatch
            )

        # Expecting True must pass
        rec = benchmark_single_trial(
            state=self.single_state,
            algorithm="wait_for_graph",
            expected_is_deadlocked=True,
            repetitions=2,
        )
        self.assertTrue(rec.is_deadlocked)

    def test_result_persistence_and_overwrite_protection(self):
        """Test saving raw JSON and processed CSV results with overwrite protection."""
        rec = benchmark_single_trial(
            state=self.single_state,
            algorithm="wait_for_graph",
            pattern="circular",
            seed=42,
            warmup_runs=1,
            repetitions=3,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test_raw.json"
            csv_path = Path(tmpdir) / "test_processed.csv"

            # 1. Save results initially
            save_raw_results([rec], json_path, overwrite=False)
            save_processed_summary_csv([rec], csv_path, overwrite=False)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())

            # 2. Re-saving with overwrite=False must raise ResultStorageError
            with self.assertRaises(ResultStorageError):
                save_raw_results([rec], json_path, overwrite=False)

            with self.assertRaises(ResultStorageError):
                save_processed_summary_csv([rec], csv_path, overwrite=False)

            # 3. Re-saving with overwrite=True must succeed
            save_raw_results([rec], json_path, overwrite=True)
            save_processed_summary_csv([rec], csv_path, overwrite=True)

            # 4. Validate JSON contents
            with open(json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self.assertEqual(raw_data["metadata"]["record_count"], 1)
            self.assertEqual(len(raw_data["records"][0]["raw_timings_us"]), 3)

            # 5. Validate CSV headers
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
            self.assertIn("mean_us", headers)
            self.assertIn("median_us", headers)
            self.assertIn("stddev_us", headers)
            self.assertIn("deadlocked_count", headers)

    def test_benchmark_config_serialization(self):
        """Test BenchmarkConfig loading from dict and JSON."""
        cfg = BenchmarkConfig(
            process_counts=[3, 5],
            resource_counts=[2, 4],
            warmup_runs=2,
            repetitions=5,
        )
        d = cfg.to_dict()
        cfg2 = BenchmarkConfig.from_dict(d)
        self.assertEqual(cfg.process_counts, cfg2.process_counts)
        self.assertEqual(cfg.warmup_runs, cfg2.warmup_runs)

    def test_invalid_parameters_rejected(self):
        """Test that invalid benchmark parameter bounds raise BenchmarkError."""
        with self.assertRaises(BenchmarkError):
            benchmark_single_trial(
                state=self.single_state,
                algorithm="wait_for_graph",
                repetitions=0,  # Must be >= 1
            )
        with self.assertRaises(BenchmarkError):
            benchmark_single_trial(
                state=self.single_state,
                algorithm="wait_for_graph",
                warmup_runs=-1,  # Must be >= 0
            )


if __name__ == "__main__":
    unittest.main()
