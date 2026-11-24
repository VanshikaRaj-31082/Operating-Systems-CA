"""
Linux Environment Identification and Hardware Discovery Module.
Complies with CA5 Section 8 (L25, L27) and Section 23 (Reproducibility).
Inspects /etc/os-release, uname, lscpu, /proc/meminfo, /proc/loadavg, and Linux utilities.
"""

import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


class LinuxEnvironment:
    """Discovers and records the host operating system, hardware, and toolchain."""

    def __init__(self, proc_root: str = "/proc") -> None:
        self.proc_root = proc_root

    def get_os_release(self) -> Dict[str, str]:
        """Parses /etc/os-release into key-value pairs."""
        os_release_path = "/etc/os-release"
        info: Dict[str, str] = {}
        if os.path.exists(os_release_path):
            try:
                with open(os_release_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            info[k.strip()] = v.strip().strip('"').strip("'")
            except Exception as e:
                info["error"] = str(e)
        else:
            info["NAME"] = platform.system()
            info["VERSION"] = platform.version()
            info["PRETTY_NAME"] = f"{platform.system()} {platform.release()}"
        return info

    def get_kernel_info(self) -> Dict[str, str]:
        """Retrieves kernel version, architecture, and system release."""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        }
        proc_version_path = os.path.join(self.proc_root, "version")
        if os.path.exists(proc_version_path):
            try:
                with open(proc_version_path, "r", encoding="utf-8") as f:
                    info["proc_version"] = f.read().strip()
            except Exception as e:
                info["proc_version_error"] = str(e)
        return info

    def get_cpu_info(self) -> Dict[str, Any]:
        """Parses /proc/cpuinfo and invokes lscpu if available."""
        cpu_info: Dict[str, Any] = {
            "logical_cores": os.cpu_count() or 1,
            "model_name": "Unknown",
            "cpu_mhz": "Unknown",
        }
        cpuinfo_path = os.path.join(self.proc_root, "cpuinfo")
        if os.path.exists(cpuinfo_path):
            try:
                with open(cpuinfo_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if ":" in line:
                            k, v = line.split(":", 1)
                            k = k.strip()
                            v = v.strip()
                            if k == "model name" and cpu_info["model_name"] == "Unknown":
                                cpu_info["model_name"] = v
                            elif k == "cpu MHz" and cpu_info["cpu_mhz"] == "Unknown":
                                cpu_info["cpu_mhz"] = v
            except Exception as e:
                cpu_info["cpuinfo_error"] = str(e)

        # Try lscpu
        if shutil.which("lscpu"):
            try:
                res = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    lscpu_dict = {}
                    for line in res.stdout.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            lscpu_dict[k.strip()] = v.strip()
                    cpu_info["lscpu"] = lscpu_dict
                    if "Model name" in lscpu_dict:
                        cpu_info["model_name"] = lscpu_dict["Model name"]
            except Exception:
                pass

        # Check CPU affinity
        if hasattr(os, "sched_getaffinity"):
            try:
                cpu_info["affinity_cpus"] = sorted(list(os.sched_getaffinity(0)))
            except Exception:
                cpu_info["affinity_cpus"] = list(range(cpu_info["logical_cores"]))
        else:
            cpu_info["affinity_cpus"] = list(range(cpu_info["logical_cores"]))

        return cpu_info

    def get_memory_info(self) -> Dict[str, Any]:
        """Parses /proc/meminfo to extract total, free, and available RAM in kB."""
        meminfo: Dict[str, Any] = {}
        meminfo_path = os.path.join(self.proc_root, "meminfo")
        if os.path.exists(meminfo_path):
            try:
                with open(meminfo_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v_parts = parts[1].strip().split()
                            if v_parts:
                                try:
                                    meminfo[k] = int(v_parts[0])  # in kB
                                except ValueError:
                                    meminfo[k] = v_parts[0]
            except Exception as e:
                meminfo["error"] = str(e)
        return meminfo

    def get_load_average(self) -> Dict[str, float]:
        """Extracts 1, 5, and 15 minute system load averages."""
        loadavg_path = os.path.join(self.proc_root, "loadavg")
        if os.path.exists(loadavg_path):
            try:
                with open(loadavg_path, "r", encoding="utf-8") as f:
                    parts = f.read().split()
                    return {
                        "load_1m": float(parts[0]),
                        "load_5m": float(parts[1]),
                        "load_15m": float(parts[2]),
                    }
            except Exception:
                pass
        try:
            loads = os.getloadavg()
            return {"load_1m": loads[0], "load_5m": loads[1], "load_15m": loads[2]}
        except (AttributeError, OSError):
            return {"load_1m": 0.0, "load_5m": 0.0, "load_15m": 0.0}

    def check_tool_availability(self) -> Dict[str, Optional[str]]:
        """Verifies presence of standard Linux engineering utilities."""
        tools = [
            "ps", "top", "lscpu", "vmstat", "iostat", "pidstat",
            "taskset", "nice", "renice", "kill", "free", "uname",
            "time", "grep", "awk", "sed", "bash", "python3", "gcc"
        ]
        return {tool: shutil.which(tool) for tool in tools}

    def collect_full_profile(self) -> Dict[str, Any]:
        """Returns the complete environmental profile."""
        return {
            "os_release": self.get_os_release(),
            "kernel": self.get_kernel_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "load_average": self.get_load_average(),
            "tools": self.check_tool_availability(),
        }


if __name__ == "__main__":
    import json
    env = LinuxEnvironment()
    print(json.dumps(env.collect_full_profile(), indent=2))
