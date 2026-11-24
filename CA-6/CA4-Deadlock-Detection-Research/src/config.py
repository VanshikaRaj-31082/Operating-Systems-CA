"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/config.py

Configuration schemas and environment metadata collection for the benchmarking framework.
"""

from __future__ import annotations

import os
import sys
import platform
import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json


@dataclass(frozen=True)
class EnvironmentMetadata:
    """System runtime and hardware execution metadata."""
    python_version: str
    python_implementation: str
    os_name: str
    os_release: str
    os_version: str
    machine: str
    processor: str
    cpu_count: Optional[int]
    timestamp_utc: str

    @classmethod
    def capture(cls) -> EnvironmentMetadata:
        """Captures host system environmental parameters at execution time."""
        return cls(
            python_version=platform.python_version(),
            python_implementation=platform.python_implementation(),
            os_name=platform.system(),
            os_release=platform.release(),
            os_version=platform.version(),
            machine=platform.machine(),
            processor=platform.processor(),
            cpu_count=os.cpu_count(),
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkConfig:
    """
    Configuration specification for a benchmark trial.

    Attributes
    ----------
    process_counts : List[int]
        List of process counts (n) to evaluate.
    resource_counts : List[int]
        List of resource type counts (m) to evaluate.
    resource_models : List[str]
        Resource models to evaluate: 'single_instance' and/or 'multi_instance'.
    patterns : List[str]
        Allocation patterns to evaluate: 'acyclic', 'circular', 'random', 'mixed'.
    algorithms : List[str]
        Detection algorithms: 'wait_for_graph' and/or 'multi_instance'.
    warmup_runs : int
        Number of untimed warmup executions to prime CPU caches and runtime.
    repetitions : int
        Number of timed repetitions for statistical metric collection.
    seeds : List[int]
        Seeds for deterministic generation.
    """
    process_counts: List[int] = field(default_factory=lambda: [5, 10])
    resource_counts: List[int] = field(default_factory=lambda: [3, 5])
    resource_models: List[str] = field(default_factory=lambda: ["single_instance", "multi_instance"])
    patterns: List[str] = field(default_factory=lambda: ["acyclic", "circular", "random", "mixed"])
    algorithms: List[str] = field(default_factory=lambda: ["wait_for_graph", "multi_instance"])
    warmup_runs: int = 3
    repetitions: int = 10
    seeds: List[int] = field(default_factory=lambda: [42])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkConfig:
        return cls(
            process_counts=list(data.get("process_counts", [5, 10])),
            resource_counts=list(data.get("resource_counts", [3, 5])),
            resource_models=list(data.get("resource_models", ["single_instance", "multi_instance"])),
            patterns=list(data.get("patterns", ["acyclic", "circular", "random", "mixed"])),
            algorithms=list(data.get("algorithms", ["wait_for_graph", "multi_instance"])),
            warmup_runs=int(data.get("warmup_runs", 3)),
            repetitions=int(data.get("repetitions", 10)),
            seeds=list(data.get("seeds", [42])),
        )

    @classmethod
    def from_json_file(cls, path: str) -> BenchmarkConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_json_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
