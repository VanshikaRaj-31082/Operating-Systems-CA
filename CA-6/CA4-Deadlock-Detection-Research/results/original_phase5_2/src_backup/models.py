"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Module: src/models.py

Mathematical Data Models for Resource Allocation and Deadlock Detection.

Strictly Enforced Invariants:
1. Dimensional Consistency:
   - Total vector: length m (number of resource types).
   - Available vector: length m.
   - Allocation matrix: shape n x m (n processes, m resource types).
   - Request matrix: shape n x m.
2. Non-Negativity:
   - Total[j] >= 1 for all j in {0, ..., m-1} (positive capacity).
   - Allocation[i][j] >= 0 for all i, j.
   - Request[i][j] >= 0 for all i, j.
   - Available[j] >= 0 for all j.
3. Resource Conservation:
   - For every resource type j in {0, ..., m-1}:
     Available[j] + sum_{i=0}^{n-1}(Allocation[i][j]) == Total[j]
4. Separation of Concerns:
   - Request[i][j] represents ACTUAL outstanding unsatisfied requests at audit time.
   - It is fundamentally distinct from Banker's Algorithm Need[i][j] (maximum future claims).
   - No Max or Need matrices are required for deadlock detection.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any


class InvariantViolation(Exception):
    """Base exception for all system state invariant violations."""
    pass


class DimensionMismatchError(InvariantViolation):
    """Raised when vector or matrix dimensions are inconsistent."""
    pass


class InvalidValueError(InvariantViolation):
    """Raised when matrix entries violate positivity or non-negativity."""
    pass


class ResourceConservationError(InvariantViolation):
    """Raised when Available[j] + sum_i(Allocation[i][j]) != Total[j]."""
    pass


class SystemState:
    """
    Immutable representation of an operating system resource allocation state
    tailored for Deadlock Detection Research.

    Parameters
    ----------
    total : List[int]
        Total instances of each resource type. Length m.
    allocation : List[List[int]]
        Resources currently allocated to each process. Shape n x m.
    request : List[List[int]]
        Outstanding unsatisfied resource requests per process. Shape n x m.
    available : Optional[List[int]]
        Available resource instances per type. Length m.
        If None, computed as Total[j] - sum_i(Allocation[i][j]).
        If provided, validated against Total and Allocation under conservation.
    process_names : Optional[List[str]]
        Human-readable identifiers for processes. Length n.
    resource_names : Optional[List[str]]
        Human-readable identifiers for resource types. Length m.
    """

    def __init__(
        self,
        total: List[int],
        allocation: List[List[int]],
        request: List[List[int]],
        available: Optional[List[int]] = None,
        process_names: Optional[List[str]] = None,
        resource_names: Optional[List[str]] = None,
    ) -> None:
        # Deep copy all raw input structures to prevent external mutation
        self._total: List[int] = list(total)
        self._allocation: List[List[int]] = [list(row) for row in allocation]
        self._request: List[List[int]] = [list(row) for row in request]

        self._n: int = len(self._allocation)
        self._m: int = len(self._total)

        # Validate basic dimensional coherence and bounds
        self._validate_dimensions()
        self._validate_value_constraints()

        # Handle Available vector and conservation
        if available is not None:
            self._available: List[int] = list(available)
            self._validate_available_dimensions()
            self._validate_available_values()
            self._validate_conservation()
        else:
            self._available = self._compute_available()
            self._validate_conservation()

        # Set or default labels
        if process_names is not None:
            if len(process_names) != self._n:
                raise DimensionMismatchError(
                    f"process_names length ({len(process_names)}) does not match process count n ({self._n})"
                )
            self._process_names: List[str] = list(process_names)
        else:
            self._process_names = [f"P{i}" for i in range(self._n)]

        if resource_names is not None:
            if len(resource_names) != self._m:
                raise DimensionMismatchError(
                    f"resource_names length ({len(resource_names)}) does not match resource count m ({self._m})"
                )
            self._resource_names: List[str] = list(resource_names)
        else:
            self._resource_names = [f"R{j}" for j in range(self._m)]

    # ─────────────────────────────────────────────────────────────────
    # Validation Logic
    # ─────────────────────────────────────────────────────────────────

    def _validate_dimensions(self) -> None:
        """Enforce strict dimensional consistency across matrices and vectors."""
        if self._n <= 0:
            raise InvalidValueError(f"Process count n must be at least 1, got {self._n}")
        if self._m <= 0:
            raise InvalidValueError(f"Resource type count m must be at least 1, got {self._m}")

        if len(self._request) != self._n:
            raise DimensionMismatchError(
                f"Request row count ({len(self._request)}) must match process count n ({self._n})"
            )

        for i, row in enumerate(self._allocation):
            if len(row) != self._m:
                raise DimensionMismatchError(
                    f"Allocation row {i} has length {len(row)}, expected m ({self._m})"
                )

        for i, row in enumerate(self._request):
            if len(row) != self._m:
                raise DimensionMismatchError(
                    f"Request row {i} has length {len(row)}, expected m ({self._m})"
                )

    def _validate_value_constraints(self) -> None:
        """Enforce positivity of Total and non-negativity of Allocation/Request."""
        for j, tot in enumerate(self._total):
            if not isinstance(tot, int) or isinstance(tot, bool):
                raise InvalidValueError(f"Total[{j}] must be an integer, got {type(tot).__name__}")
            if tot < 1:
                raise InvalidValueError(f"Total[{j}] must be positive (>= 1), got {tot}")

        for i in range(self._n):
            for j in range(self._m):
                alloc_val = self._allocation[i][j]
                if not isinstance(alloc_val, int) or isinstance(alloc_val, bool):
                    raise InvalidValueError(
                        f"Allocation[{i}][{j}] must be an integer, got {type(alloc_val).__name__}"
                    )
                if alloc_val < 0:
                    raise InvalidValueError(
                        f"Allocation[{i}][{j}] must be non-negative, got {alloc_val}"
                    )

                req_val = self._request[i][j]
                if not isinstance(req_val, int) or isinstance(req_val, bool):
                    raise InvalidValueError(
                        f"Request[{i}][{j}] must be an integer, got {type(req_val).__name__}"
                    )
                if req_val < 0:
                    raise InvalidValueError(
                        f"Request[{i}][{j}] must be non-negative, got {req_val}"
                    )

    def _validate_available_dimensions(self) -> None:
        """Enforce Available vector length matches m."""
        if len(self._available) != self._m:
            raise DimensionMismatchError(
                f"Available vector length ({len(self._available)}) must match m ({self._m})"
            )

    def _validate_available_values(self) -> None:
        """Enforce Available vector entries are non-negative integers."""
        for j, avail in enumerate(self._available):
            if not isinstance(avail, int) or isinstance(avail, bool):
                raise InvalidValueError(f"Available[{j}] must be an integer, got {type(avail).__name__}")
            if avail < 0:
                raise InvalidValueError(f"Available[{j}] must be non-negative, got {avail}")

    def _compute_available(self) -> List[int]:
        """Compute Available[j] = Total[j] - sum_i(Allocation[i][j])."""
        available = []
        for j in range(self._m):
            allocated_sum = sum(self._allocation[i][j] for i in range(self._n))
            avail = self._total[j] - allocated_sum
            if avail < 0:
                raise ResourceConservationError(
                    f"Resource {j} over-allocated: Total[{j}]={self._total[j]} < allocated={allocated_sum}"
                )
            available.append(avail)
        return available

    def _validate_conservation(self) -> None:
        """
        Enforce strict conservation law:
        Available[j] + sum_i(Allocation[i][j]) == Total[j] for all j.
        """
        for j in range(self._m):
            allocated_sum = sum(self._allocation[i][j] for i in range(self._n))
            total_sum = self._available[j] + allocated_sum
            if total_sum != self._total[j]:
                raise ResourceConservationError(
                    f"Resource conservation violated for resource {j}: "
                    f"Available[{j}] ({self._available[j]}) + sum(Allocation) ({allocated_sum}) "
                    f"= {total_sum} != Total[{j}] ({self._total[j]})"
                )

    # ─────────────────────────────────────────────────────────────────
    # Public Read-Only Properties (Returning Deep Copies)
    # ─────────────────────────────────────────────────────────────────

    @property
    def n(self) -> int:
        """Number of processes."""
        return self._n

    @property
    def m(self) -> int:
        """Number of resource types."""
        return self._m

    @property
    def total(self) -> List[int]:
        """Total resource capacities vector. Returns a deep copy."""
        return list(self._total)

    @property
    def allocation(self) -> List[List[int]]:
        """Current resource allocation matrix (n x m). Returns a deep copy."""
        return [list(row) for row in self._allocation]

    @property
    def request(self) -> List[List[int]]:
        """Outstanding request matrix (n x m). Returns a deep copy."""
        return [list(row) for row in self._request]

    @property
    def available(self) -> List[int]:
        """Currently available resource instances vector. Returns a deep copy."""
        return list(self._available)

    @property
    def process_names(self) -> List[str]:
        """Process identifier labels."""
        return list(self._process_names)

    @property
    def resource_names(self) -> List[str]:
        """Resource type labels."""
        return list(self._resource_names)

    @property
    def is_single_instance(self) -> bool:
        """Returns True if every resource type has Total == 1."""
        return all(cap == 1 for cap in self._total)

    # ─────────────────────────────────────────────────────────────────
    # Serialization & Inspection
    # ─────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to standard dictionary representation."""
        return {
            "n": self._n,
            "m": self._m,
            "total": list(self._total),
            "allocation": [list(row) for row in self._allocation],
            "request": [list(row) for row in self._request],
            "available": list(self._available),
            "process_names": list(self._process_names),
            "resource_names": list(self._resource_names),
            "is_single_instance": self.is_single_instance,
        }

    def __repr__(self) -> str:
        return (
            f"SystemState(n={self._n}, m={self._m}, "
            f"total={self._total}, available={self._available}, "
            f"single_instance={self.is_single_instance})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SystemState):
            return False
        return (
            self._total == other._total
            and self._allocation == other._allocation
            and self._request == other._request
            and self._available == other._available
        )
