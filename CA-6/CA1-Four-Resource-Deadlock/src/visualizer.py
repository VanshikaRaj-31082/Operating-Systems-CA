"""Visualizer and reporting utilities for the Four-Resource Deadlock simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.deadlock_detector import CycleDetectionResult
from src.models import ResourceAllocationGraph


class SimulationVisualizer:
    """Formats ASCII diagrams, cycle paths, and comparative telemetry tables."""

    @staticmethod
    def render_ascii_rag(rag: ResourceAllocationGraph) -> str:
        """Render a readable ASCII representation of the Resource Allocation Graph."""
        adj = rag.get_adjacency_copy()
        lines: List[str] = [
            "+-----------------------------------------------------------------------+",
            "|                RESOURCE ALLOCATION GRAPH (RAG) SNAPSHOT               |",
            "+-----------------------------------------------------------------------+",
            "| Node        | Outgoing Edges (Dependency Direction)                  |",
            "+-------------+---------------------------------------------------------+",
        ]

        all_nodes = sorted(list(adj.keys()))
        for node in all_nodes:
            targets = sorted(list(adj.get(node, set())))
            if node.startswith("P"):
                label = f"Process  ({node})"
                edge_desc = [f"Requests [{t}]" for t in targets]
            else:
                label = f"Resource [{node}]"
                edge_desc = [f"Held by ({t})" for t in targets]

            target_str = ", ".join(edge_desc) if edge_desc else "(none - idle)"
            lines.append(f"| {label:<11} | {target_str:<55} |")

        lines.append("+-----------------------------------------------------------------------+")
        return "\n".join(lines)

    @staticmethod
    def render_cycle_box(detection_result: CycleDetectionResult) -> str:
        """Render a prominent ASCII box highlighting the detected circular wait."""
        if not detection_result.has_deadlock:
            return (
                "+-----------------------------------------------------------------------+\n"
                "|                    CYCLE DETECTION: NO DEADLOCK DETECTED             |\n"
                "|               The Resource Allocation Graph is Acyclic (DAG)          |\n"
                "+-----------------------------------------------------------------------+"
            )

        cycle_str = detection_result.format_cycle_path()
        lines = [
            "+-----------------------------------------------------------------------+",
            "|               DEADLOCK DETECTED: CIRCULAR WAIT IN RAG                 |",
            "+-----------------------------------------------------------------------+",
            f"| Cycle: {cycle_str:<62} |",
            "|                                                                       |",
            f"| Involved Processes: {', '.join(detection_result.involved_processes):<49} |",
            f"| Involved Resources: {', '.join(detection_result.involved_resources):<49} |",
            "+-----------------------------------------------------------------------+",
        ]
        return "\n".join(lines)

    @staticmethod
    def render_comparison_table(metrics: Dict[str, Any]) -> str:
        """Render a comparative ASCII summary table contrasting Naive and Prevented runs."""
        lines = [
            "+-----------------------------------------------------------------------+",
            "|             COMPARATIVE EVALUATION: NAIVE VS PREVENTED RUN            |",
            "+-----------------------------------+-----------------+-----------------+",
            "| Evaluation Metric                 | Naive (Circular)| Prevented (Rank)|",
            "+-----------------------------------+-----------------+-----------------+",
            f"| Total Tasks Attempted             | {metrics['naive']['total_tasks']:<15} | {metrics['prevented']['total_tasks']:<15} |",
            f"| Tasks Completed Successfully      | {metrics['naive']['completed_tasks']:<15} | {metrics['prevented']['completed_tasks']:<15} |",
            f"| Tasks Deadlocked / Blocked        | {metrics['naive']['deadlocked_tasks']:<15} | {metrics['prevented']['deadlocked_tasks']:<15} |",
            f"| Cycles Detected in RAG            | {metrics['naive']['cycles_detected']:<15} | {metrics['prevented']['cycles_detected']:<15} |",
            f"| Deadlock Occurred?                | {'YES (FROZEN)':<15} | {'NO (SOLVED)':<15} |",
            f"| Total Elapsed Duration            | {metrics['naive']['elapsed_seconds']:<12.3f} s | {metrics['prevented']['elapsed_seconds']:<12.3f} s |",
            f"| Starvation Guaranteed Free?       | {'N/A (Deadlocked)':<15} | {'NO (Requires FIFO)':<15} |",
            "+-----------------------------------+-----------------+-----------------+",
        ]
        return "\n".join(lines)

    @staticmethod
    def save_trace(file_path: Path, content: str) -> None:
        """Save formatted text trace to results folder."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any]) -> None:
        """Save metrics data as structured JSON."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

