"""
Unit tests for Investigation Runner and Data Serialization (src/investigation_runner.py).
"""

import os
import tempfile
import unittest
from src.investigation_runner import InvestigationRunner, compute_stats


class TestRunnerAndSerialization(unittest.TestCase):

    def test_compute_stats_empty(self) -> None:
        stats = compute_stats([])
        self.assertIsNone(stats["mean"])
        self.assertIsNone(stats["stddev"])

    def test_compute_stats_single(self) -> None:
        stats = compute_stats([42.0])
        self.assertEqual(stats["mean"], 42.0)
        self.assertEqual(stats["median"], 42.0)
        self.assertEqual(stats["min"], 42.0)
        self.assertEqual(stats["max"], 42.0)
        self.assertIsNone(stats["stddev"])  # Sample stddev requires N > 1

    def test_compute_stats_multiple(self) -> None:
        stats = compute_stats([10.0, 20.0, 30.0])
        self.assertEqual(stats["mean"], 20.0)
        self.assertEqual(stats["median"], 20.0)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 30.0)
        self.assertEqual(stats["stddev"], 10.0)

    def test_runner_initialization_and_config(self) -> None:
        runner = InvestigationRunner(config_path="config/experiment_config.json")
        self.assertEqual(runner.config["project"], "CA5-Linux-Systems-Engineering")
        self.assertEqual(runner.config["challenge_id"], "L38")
        self.assertTrue(os.path.exists(runner.raw_dir))
        self.assertTrue(os.path.exists(runner.processed_dir))
        self.assertTrue(os.path.exists(runner.logs_dir))


if __name__ == "__main__":
    unittest.main()
