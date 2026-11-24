"""
CA2 - Deadlock Detection and Avoidance
Phase 5 Tests: Performance Benchmarking & Metric Collection.

Test Categories:
    TestComputeMetrics          - Statistical metric computations (mean, median, min, max, stdev).
    TestTimingRunners           - Core timer functions (repetitions, warmup, timing bounds).
    TestSingleWorkloadBenchmark - Execution and result structure for single workload evaluations.
    TestScalingBenchmark        - Multi-dimensional scaling benchmark across (n, m, workload types).
    TestOperationalSimulation   - Cumulative overhead comparison (per-request vs periodic sweeps).
    TestExportUtilities         - CSV and JSON file exports, headers, round-trip serialization.
    TestInputValidation         - Rejection of invalid repetitions, warmup, dimensions, etc.
"""

import csv
import json
import os
import shutil
import tempfile
import unittest
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
)

from src.models import SystemState
from src.workload_generator import make_safe_state, make_zero_request
from src.benchmark import (
    BenchmarkError,
    BenchmarkResult,
    compute_metrics,
    time_bankers_safety,
    time_deadlock_detection,
    benchmark_single_workload,
    run_scaling_benchmark,
    run_operational_overhead_simulation,
    export_to_csv,
    export_to_json,
    CSV_FIELDNAMES,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Statistical Metric Calculations
# ═══════════════════════════════════════════════════════════════════════

class TestComputeMetrics(unittest.TestCase):
    """Verify statistical computations against hand-verified numbers."""

    def test_basic_metrics_odd_length(self):
        sample = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_metrics(sample)
        self.assertAlmostEqual(stats["mean"], 30.0)
        self.assertAlmostEqual(stats["median"], 30.0)
        self.assertAlmostEqual(stats["min"], 10.0)
        self.assertAlmostEqual(stats["max"], 50.0)
        self.assertAlmostEqual(stats["stdev"], 15.811388, places=5)

    def test_basic_metrics_even_length(self):
        sample = [10.0, 20.0, 40.0, 50.0]
        stats = compute_metrics(sample)
        self.assertAlmostEqual(stats["mean"], 30.0)
        self.assertAlmostEqual(stats["median"], 30.0)  # average of 20 and 40

    def test_single_element_sample(self):
        sample = [42.5]
        stats = compute_metrics(sample)
        self.assertAlmostEqual(stats["mean"], 42.5)
        self.assertAlmostEqual(stats["median"], 42.5)
        self.assertAlmostEqual(stats["stdev"], 0.0)

    def test_empty_sample_raises_error(self):
        with self.assertRaises(BenchmarkError):
            compute_metrics([])


# ═══════════════════════════════════════════════════════════════════════
# 2. Timing Runners
# ═══════════════════════════════════════════════════════════════════════

class TestTimingRunners(unittest.TestCase):
    """Verify timing execution, repetition counts, and warmup."""

    def setUp(self):
        self.state = make_safe_state(4, 2, total_per_type=20, seed=42)
        self.req = make_zero_request(4, 2)

    def test_bankers_timing_sample_count(self):
        times = time_bankers_safety(self.state, repetitions=5, warmup_runs=1)
        self.assertEqual(len(times), 5)
        for t in times:
            self.assertGreater(t, 0.0)

    def test_detector_timing_sample_count(self):
        times = time_deadlock_detection(self.state, self.req, repetitions=6, warmup_runs=2)
        self.assertEqual(len(times), 6)
        for t in times:
            self.assertGreater(t, 0.0)

    def test_zero_warmup_runs_allowed(self):
        times = time_bankers_safety(self.state, repetitions=3, warmup_runs=0)
        self.assertEqual(len(times), 3)

    def test_invalid_repetition_counts(self):
        with self.assertRaises(BenchmarkError):
            time_bankers_safety(self.state, repetitions=0)
        with self.assertRaises(BenchmarkError):
            time_deadlock_detection(self.state, self.req, repetitions=-1)

    def test_negative_warmup_raises_error(self):
        with self.assertRaises(BenchmarkError):
            time_bankers_safety(self.state, repetitions=5, warmup_runs=-1)


# ═══════════════════════════════════════════════════════════════════════
# 3. Single Workload Benchmark
# ═══════════════════════════════════════════════════════════════════════

class TestSingleWorkloadBenchmark(unittest.TestCase):
    """Verify benchmark_single_workload returns correct BenchmarkResult schemas."""

    def setUp(self):
        self.state = make_safe_state(5, 3, total_per_type=20, seed=12)
        self.req = make_zero_request(5, 3)

    def test_evaluates_both_algorithms_by_default(self):
        results = benchmark_single_workload(
            self.state, self.req, workload_type="safe", repetitions=4, seed=12
        )
        self.assertEqual(len(results), 2)
        alg_names = {r.algorithm for r in results}
        self.assertEqual(alg_names, {"bankers_safety", "deadlock_detection"})

    def test_schema_fields(self):
        results = benchmark_single_workload(
            self.state, self.req, workload_type="safe", repetitions=3, seed=12
        )
        res = results[0]
        self.assertIsInstance(res, BenchmarkResult)
        self.assertEqual(res.n, 5)
        self.assertEqual(res.m, 3)
        self.assertEqual(res.workload_type, "safe")
        self.assertGreater(res.mean_time_us, 0.0)
        self.assertGreaterEqual(res.min_time_us, 0.0)
        self.assertGreaterEqual(res.max_time_us, res.min_time_us)
        self.assertEqual(res.repetitions, 3)
        self.assertEqual(len(res.raw_times_us), 3)

    def test_to_dict_serialization(self):
        results = benchmark_single_workload(
            self.state, self.req, workload_type="safe", repetitions=2, seed=12
        )
        d = results[0].to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["algorithm"], "bankers_safety")
        self.assertEqual(d["n"], 5)
        self.assertIsInstance(d["raw_times_us"], list)


# ═══════════════════════════════════════════════════════════════════════
# 4. Multi-Dimensional Scaling Benchmark
# ═══════════════════════════════════════════════════════════════════════

class TestScalingBenchmark(unittest.TestCase):
    """Verify run_scaling_benchmark across dimensions and workload types."""

    def test_scaling_grid_counts(self):
        # 2 process counts x 2 resource counts x 2 workload types x 2 algorithms = 16 records
        results = run_scaling_benchmark(
            process_counts=[3, 5],
            resource_counts=[2, 3],
            workload_types=("safe", "deadlocked"),
            repetitions=3,
            warmup_runs=1,
            seed=42,
        )
        expected_count = 2 * 2 * 2 * 2
        self.assertEqual(len(results), expected_count)

    def test_scaling_benchmark_reproducibility(self):
        # Two runs with identical parameters must yield identical configuration shapes
        r1 = run_scaling_benchmark([4], [2], workload_types=("safe",), repetitions=2, seed=77)
        r2 = run_scaling_benchmark([4], [2], workload_types=("safe",), repetitions=2, seed=77)
        self.assertEqual(len(r1), len(r2))
        self.assertEqual(r1[0].n, r2[0].n)
        self.assertEqual(r1[0].m, r2[0].m)
        self.assertEqual(r1[0].seed, r2[0].seed)
        self.assertAlmostEqual(r1[0].rho_max, r2[0].rho_max)


# ═══════════════════════════════════════════════════════════════════════
# 5. Operational Overhead Simulation
# ═══════════════════════════════════════════════════════════════════════

class TestOperationalSimulation(unittest.TestCase):
    """Verify per-request vs periodic sweep operational overhead simulation."""

    def test_operational_simulation_structure(self):
        state = make_safe_state(4, 3, total_per_type=20, seed=10)
        sim = run_operational_overhead_simulation(
            state, request_stream_length=30, detection_sweep_interval=5, seed=10
        )
        self.assertEqual(sim["n"], 4)
        self.assertEqual(sim["m"], 3)
        self.assertEqual(sim["request_stream_length"], 30)
        self.assertEqual(sim["strategy_a"]["checks_executed"], 30)
        self.assertEqual(sim["strategy_b"]["checks_executed"], 6)  # 30 / 5
        self.assertGreater(sim["strategy_a"]["cumulative_time_us"], 0.0)
        self.assertGreater(sim["strategy_b"]["cumulative_time_us"], 0.0)
        self.assertIn("cumulative_overhead_ratio_A_vs_B", sim)

    def test_invalid_simulation_parameters(self):
        state = make_safe_state(3, 2, total_per_type=20, seed=10)
        with self.assertRaises(BenchmarkError):
            run_operational_overhead_simulation(state, request_stream_length=0)
        with self.assertRaises(BenchmarkError):
            run_operational_overhead_simulation(state, detection_sweep_interval=0)


# ═══════════════════════════════════════════════════════════════════════
# 6. Export Utilities (CSV and JSON)
# ═══════════════════════════════════════════════════════════════════════

class TestExportUtilities(unittest.TestCase):
    """Verify export to CSV and JSON formats."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        state = make_safe_state(4, 2, total_per_type=20, seed=5)
        req = make_zero_request(4, 2)
        self.results = benchmark_single_workload(
            state, req, workload_type="safe", repetitions=3, seed=5
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_to_csv_creates_valid_file(self):
        csv_path = os.path.join(self.temp_dir, "test_out.csv")
        export_to_csv(self.results, csv_path)
        self.assertTrue(os.path.exists(csv_path))

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, CSV_FIELDNAMES)
            rows = list(reader)
            self.assertEqual(len(rows), len(self.results))
            self.assertEqual(rows[0]["algorithm"], "bankers_safety")
            self.assertEqual(int(rows[0]["n"]), 4)
            self.assertEqual(int(rows[0]["m"]), 2)

    def test_export_to_json_creates_valid_file(self):
        json_path = os.path.join(self.temp_dir, "test_out.json")
        export_to_json(self.results, json_path, extra_metadata={"experiment": "test"})
        self.assertTrue(os.path.exists(json_path))

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("metadata", data)
            self.assertIn("results", data)
            self.assertEqual(data["metadata"]["experiment"], "test")
            self.assertEqual(len(data["results"]), len(self.results))
            self.assertEqual(data["results"][0]["algorithm"], "bankers_safety")

    def test_empty_results_export_raises_error(self):
        csv_path = os.path.join(self.temp_dir, "empty.csv")
        json_path = os.path.join(self.temp_dir, "empty.json")
        with self.assertRaises(BenchmarkError):
            export_to_csv([], csv_path)
        with self.assertRaises(BenchmarkError):
            export_to_json([], json_path)


# ═══════════════════════════════════════════════════════════════════════
# 7. Input Validation
# ═══════════════════════════════════════════════════════════════════════

class TestInputValidation(unittest.TestCase):
    """Verify validation of benchmark inputs and configurations."""

    def test_empty_dimension_lists_raise_error(self):
        with self.assertRaises(BenchmarkError):
            run_scaling_benchmark(process_counts=[], resource_counts=[3])
        with self.assertRaises(BenchmarkError):
            run_scaling_benchmark(process_counts=[5], resource_counts=[])

    def test_unknown_workload_type_raises_error(self):
        with self.assertRaises(BenchmarkError):
            run_scaling_benchmark(
                process_counts=[4],
                resource_counts=[2],
                workload_types=("non_existent_type",),
            )


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
