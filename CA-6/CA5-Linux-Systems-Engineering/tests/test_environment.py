"""
Unit tests for Linux Environment Discovery (src/environment.py).
"""

import os
import unittest
from src.environment import LinuxEnvironment


class TestLinuxEnvironment(unittest.TestCase):

    def setUp(self) -> None:
        self.env = LinuxEnvironment()

    def test_get_os_release_structure(self) -> None:
        os_rel = self.env.get_os_release()
        self.assertIsInstance(os_rel, dict)
        self.assertTrue("NAME" in os_rel or "error" in os_rel or "PRETTY_NAME" in os_rel)

    def test_get_kernel_info(self) -> None:
        kernel_info = self.env.get_kernel_info()
        self.assertIn("system", kernel_info)
        self.assertIn("release", kernel_info)
        self.assertIn("machine", kernel_info)
        self.assertIn("python_version", kernel_info)

    def test_get_cpu_info(self) -> None:
        cpu_info = self.env.get_cpu_info()
        self.assertIn("logical_cores", cpu_info)
        self.assertGreaterEqual(cpu_info["logical_cores"], 1)
        self.assertIn("affinity_cpus", cpu_info)
        self.assertIsInstance(cpu_info["affinity_cpus"], list)

    def test_get_memory_info(self) -> None:
        mem_info = self.env.get_memory_info()
        self.assertIsInstance(mem_info, dict)

    def test_get_load_average(self) -> None:
        load = self.env.get_load_average()
        self.assertIn("load_1m", load)
        self.assertIn("load_5m", load)
        self.assertIn("load_15m", load)
        self.assertGreaterEqual(load["load_1m"], 0.0)

    def test_check_tool_availability(self) -> None:
        tools = self.env.check_tool_availability()
        self.assertIn("python3", tools)
        self.assertIn("ps", tools)
        self.assertIn("uname", tools)

    def test_collect_full_profile(self) -> None:
        profile = self.env.collect_full_profile()
        self.assertIn("os_release", profile)
        self.assertIn("kernel", profile)
        self.assertIn("cpu", profile)
        self.assertIn("memory", profile)
        self.assertIn("tools", profile)


if __name__ == "__main__":
    unittest.main()
