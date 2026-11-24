"""
Linux /proc Process Explorer and Thread Inspector Module.
Addresses CA5 Official Challenge L25 (/proc Process Explorer) and L26.
Parses /proc/<pid>/status, /proc/<pid>/stat, /proc/<pid>/wchan, and thread status.
Safely extracts context-switch counts (voluntary/non-voluntary) and thread states.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple


class ProcExplorer:
    """Provides methods to inspect process and thread state via /proc."""

    def __init__(self, proc_root: str = "/proc") -> None:
        self.proc_root = proc_root

    def is_proc_available(self) -> bool:
        """Checks if the /proc virtual filesystem is mounted and accessible."""
        return os.path.exists(self.proc_root) and os.path.isdir(self.proc_root)

    def parse_proc_status(self, pid: int) -> Dict[str, Any]:
        """
        Parses /proc/<pid>/status into a structured dictionary.
        Extracts Name, State, Tgid, Pid, PPid, Threads, VmSize, VmRSS,
        voluntary_ctxt_switches, and nonvoluntary_ctxt_switches.
        """
        status_path = os.path.join(self.proc_root, str(pid), "status")
        if not os.path.exists(status_path):
            raise ProcessLookupError(f"Process {pid} not found in {self.proc_root}")

        data: Dict[str, Any] = {"pid": pid}
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip()
                        if k in ("voluntary_ctxt_switches", "nonvoluntary_ctxt_switches", "Threads", "PPid", "Tgid"):
                            try:
                                data[k] = int(v)
                            except ValueError:
                                data[k] = v
                        elif k in ("VmSize", "VmRSS", "VmPeak", "VmData", "VmStk"):
                            v_parts = v.split()
                            try:
                                data[k] = int(v_parts[0])  # in kB
                            except (ValueError, IndexError):
                                data[k] = v
                        else:
                            data[k] = v
        except FileNotFoundError:
            raise ProcessLookupError(f"Process {pid} terminated during inspection.")
        except PermissionError:
            data["error"] = "PermissionDenied"
        return data

    def parse_proc_stat(self, pid: int) -> Dict[str, Any]:
        """
        Parses /proc/<pid>/stat into standardized kernel process fields.
        Field reference from Linux man 5 proc:
        (1) pid, (2) comm, (3) state, (4) ppid, (14) utime, (15) stime,
        (18) priority, (19) nice, (20) num_threads, (23) vsize, (24) rss.
        """
        stat_path = os.path.join(self.proc_root, str(pid), "stat")
        if not os.path.exists(stat_path):
            raise ProcessLookupError(f"Process {pid} not found in {self.proc_root}")

        try:
            with open(stat_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except FileNotFoundError:
            raise ProcessLookupError(f"Process {pid} terminated during inspection.")

        # comm can contain spaces and parentheses, e.g. (python3), so split around the last ')'
        rparen_idx = content.rfind(")")
        if rparen_idx == -1:
            tokens = content.split()
            pid_str = tokens[0]
            comm = ""
            rest = tokens[1:]
        else:
            first_part = content[:rparen_idx]
            rest_part = content[rparen_idx + 1:].strip()
            lparen_idx = first_part.find("(")
            pid_str = first_part[:lparen_idx].strip()
            comm = first_part[lparen_idx + 1:].strip()
            rest = rest_part.split()

        data: Dict[str, Any] = {
            "pid": int(pid_str),
            "comm": comm,
            "state": rest[0] if len(rest) > 0 else "Unknown",
            "ppid": int(rest[1]) if len(rest) > 1 else -1,
            "utime_ticks": int(rest[11]) if len(rest) > 11 else 0,
            "stime_ticks": int(rest[12]) if len(rest) > 12 else 0,
            "priority": int(rest[15]) if len(rest) > 15 else 0,
            "nice": int(rest[16]) if len(rest) > 16 else 0,
            "num_threads": int(rest[17]) if len(rest) > 17 else 1,
            "vsize_bytes": int(rest[20]) if len(rest) > 20 else 0,
            "rss_pages": int(rest[21]) if len(rest) > 21 else 0,
        }
        return data

    def get_thread_ids(self, pid: int) -> List[int]:
        """Lists active thread IDs (TIDs) from /proc/<pid>/task/."""
        task_dir = os.path.join(self.proc_root, str(pid), "task")
        if not os.path.exists(task_dir):
            return []
        try:
            entries = os.listdir(task_dir)
            tids = [int(e) for e in entries if e.isdigit()]
            return sorted(tids)
        except (FileNotFoundError, PermissionError):
            return []

    def get_thread_wchan(self, pid: int, tid: int) -> str:
        """
        Reads /proc/<pid>/task/<tid>/wchan.
        Returns the kernel wait channel function symbol (e.g. 'futex_wait_queue', '0').
        """
        wchan_path = os.path.join(self.proc_root, str(pid), "task", str(tid), "wchan")
        if not os.path.exists(wchan_path):
            return "unavailable"
        try:
            with open(wchan_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError):
            return "unavailable"

    def get_thread_details(self, pid: int) -> List[Dict[str, Any]]:
        """Inspects all threads of a process, extracting state and wchan."""
        tids = self.get_thread_ids(pid)
        results = []
        for tid in tids:
            thread_info: Dict[str, Any] = {"tid": tid}
            status_path = os.path.join(self.proc_root, str(pid), "task", str(tid), "status")
            if os.path.exists(status_path):
                try:
                    with open(status_path, "r", encoding="utf-8") as f:
                        for line in f:
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                k = parts[0].strip()
                                v = parts[1].strip()
                                if k in ("State", "voluntary_ctxt_switches", "nonvoluntary_ctxt_switches"):
                                    if "ctxt_switches" in k:
                                        thread_info[k] = int(v)
                                    else:
                                        thread_info[k] = v
                except (FileNotFoundError, PermissionError):
                    pass
            thread_info["wchan"] = self.get_thread_wchan(pid, tid)
            results.append(thread_info)
        return results

    def get_context_switches(self, pid: int) -> Tuple[int, int]:
        """
        Retrieves (voluntary_ctxt_switches, nonvoluntary_ctxt_switches) for process <pid>.
        Returns (0, 0) if unavailable.
        """
        try:
            status = self.parse_proc_status(pid)
            vol = status.get("voluntary_ctxt_switches", 0)
            nonvol = status.get("nonvoluntary_ctxt_switches", 0)
            return int(vol), int(nonvol)
        except Exception:
            return 0, 0


class ContextSwitchTracker:
    """Helper context manager to track context switch deltas during workload execution."""

    def __init__(self, pid: Optional[int] = None, explorer: Optional[ProcExplorer] = None) -> None:
        self.pid = pid or os.getpid()
        self.explorer = explorer or ProcExplorer()
        self.start_vol = 0
        self.start_nonvol = 0
        self.delta_vol = 0
        self.delta_nonvol = 0

    def start(self) -> None:
        self.start_vol, self.start_nonvol = self.explorer.get_context_switches(self.pid)

    def stop(self) -> Tuple[int, int]:
        end_vol, end_nonvol = self.explorer.get_context_switches(self.pid)
        self.delta_vol = max(0, end_vol - self.start_vol)
        self.delta_nonvol = max(0, end_nonvol - self.start_nonvol)
        return self.delta_vol, self.delta_nonvol

    def __enter__(self) -> "ContextSwitchTracker":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


if __name__ == "__main__":
    import json
    explorer = ProcExplorer()
    my_pid = os.getpid()
    print(f"Inspecting self PID {my_pid}...")
    try:
        print(json.dumps(explorer.parse_proc_status(my_pid), indent=2))
        print("Threads:", explorer.get_thread_details(my_pid))
    except Exception as ex:
        print(f"Error inspecting self: {ex}")
