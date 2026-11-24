"""
Unit tests for /proc Process Explorer and Thread Inspector (src/proc_explorer.py).
"""

import os
import tempfile
import unittest
from src.proc_explorer import ContextSwitchTracker, ProcExplorer


class TestProcExplorer(unittest.TestCase):

    def setUp(self) -> None:
        self.explorer = ProcExplorer()

    def test_proc_availability_check(self) -> None:
        avail = self.explorer.is_proc_available()
        self.assertIsInstance(avail, bool)

    def test_parse_proc_status_nonexistent_pid(self) -> None:
        with self.assertRaises(ProcessLookupError):
            self.explorer.parse_proc_status(99999999)

    def test_parse_proc_stat_nonexistent_pid(self) -> None:
        with self.assertRaises(ProcessLookupError):
            self.explorer.parse_proc_stat(99999999)

    def test_mock_proc_status_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pid = 1234
            proc_pid_dir = os.path.join(tmpdir, str(pid))
            os.makedirs(proc_pid_dir)
            status_file = os.path.join(proc_pid_dir, "status")
            with open(status_file, "w") as f:
                f.write("Name:\tpython3\n")
                f.write("State:\tS (sleeping)\n")
                f.write("Tgid:\t1234\n")
                f.write("Pid:\t1234\n")
                f.write("PPid:\t1000\n")
                f.write("Threads:\t4\n")
                f.write("VmSize:\t  102400 kB\n")
                f.write("VmRSS:\t   25600 kB\n")
                f.write("voluntary_ctxt_switches:\t450\n")
                f.write("nonvoluntary_ctxt_switches:\t25\n")

            mock_explorer = ProcExplorer(proc_root=tmpdir)
            data = mock_explorer.parse_proc_status(pid)
            self.assertEqual(data["pid"], 1234)
            self.assertEqual(data["Name"], "python3")
            self.assertEqual(data["State"], "S (sleeping)")
            self.assertEqual(data["Threads"], 4)
            self.assertEqual(data["VmSize"], 102400)
            self.assertEqual(data["VmRSS"], 25600)
            self.assertEqual(data["voluntary_ctxt_switches"], 450)
            self.assertEqual(data["nonvoluntary_ctxt_switches"], 25)

    def test_mock_proc_stat_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pid = 5678
            proc_pid_dir = os.path.join(tmpdir, str(pid))
            os.makedirs(proc_pid_dir)
            stat_file = os.path.join(proc_pid_dir, "stat")
            # 5678 (worker_thread) S 1000 ... 52 fields
            tokens = [
                "5678", "(worker_thread)", "S", "1000", "5678", "5678", "0", "-1",
                "4194304", "100", "0", "0", "0", "150", "30", "0", "0", "20",
                "0", "4", "0", "100000", "50000000", "12500"
            ]
            with open(stat_file, "w") as f:
                f.write(" ".join(tokens) + "\n")

            mock_explorer = ProcExplorer(proc_root=tmpdir)
            stat_data = mock_explorer.parse_proc_stat(pid)
            self.assertEqual(stat_data["pid"], 5678)
            self.assertEqual(stat_data["comm"], "worker_thread")
            self.assertEqual(stat_data["state"], "S")
            self.assertEqual(stat_data["ppid"], 1000)
            self.assertEqual(stat_data["utime_ticks"], 150)
            self.assertEqual(stat_data["stime_ticks"], 30)
            self.assertEqual(stat_data["priority"], 20)
            self.assertEqual(stat_data["nice"], 0)
            self.assertEqual(stat_data["num_threads"], 4)

    def test_context_switch_tracker(self) -> None:
        tracker = ContextSwitchTracker(pid=os.getpid(), explorer=self.explorer)
        tracker.start()
        delta_v, delta_nv = tracker.stop()
        self.assertGreaterEqual(delta_v, 0)
        self.assertGreaterEqual(delta_nv, 0)


if __name__ == "__main__":
    unittest.main()
