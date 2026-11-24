"""
CA4 Detectors Package: Single-Instance (WFG) and Multi-Instance Deadlock Detection.
"""

from src.detectors.wait_for_graph import (
    WFGResult,
    detect_wfg_deadlock,
    build_wait_for_graph,
    find_elementary_cycles,
    find_blocked_processes,
)
from src.detectors.multi_instance_detector import (
    MultiInstanceResult,
    detect_multi_instance_deadlock,
)

__all__ = [
    "WFGResult",
    "detect_wfg_deadlock",
    "build_wait_for_graph",
    "find_elementary_cycles",
    "find_blocked_processes",
    "MultiInstanceResult",
    "detect_multi_instance_deadlock",
]
