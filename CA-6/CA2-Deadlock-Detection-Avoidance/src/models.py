"""
CA2 - Deadlock Detection and Avoidance
Core data models with strict matrix invariant enforcement.

This module provides the SystemState class, which represents the complete
resource allocation state of a system with n processes and m resource types.

Strictly Enforced Invariants:
    1. Non-negativity:  All matrix/vector entries >= 0.
    2. Positive capacity:  Total[j] > 0 for every resource type j.
    3. Dimensional consistency:  All matrices are n x m, all vectors length m.
    4. Allocation upper bound:  Allocation[i][j] <= Max[i][j] for all i, j.
    5. Need definition:  Need[i][j] = Max[i][j] - Allocation[i][j].
    6. Resource conservation:
           Available[j] + sum_i(Allocation[i][j]) = Total[j]  for all j.
       Equivalently, Available[j] >= 0 (no over-allocation).

Per-Resource Pressure Metric:
    rho_j = sum_i(Need[i][j]) / Total[j]

    This is a dimensionless ratio measuring outstanding demand relative to
    total system capacity for each resource type.  It is NOT a probability.
    Values greater than 1.0 are expected and indicate that the system cannot
    satisfy all worst-case claims simultaneously from a single resource pool.

    The system bottleneck pressure is rho_max = max_j(rho_j).
"""

from __future__ import annotations
from typing import List, Tuple


class InvariantViolation(Exception):
    """Raised when a matrix invariant is violated during validation."""
    pass


class SystemState:
    """
    Immutable representation of a resource allocation system state.

    Construction validates all invariants and computes derived matrices
    (Need, Available).  Once constructed, the state cannot be mutated.
    Properties return deep copies to prevent external corruption.

    Parameters
    ----------
    total : list[int]
        Total instances of each resource type.  Length m.
    max_claim : list[list[int]]
        Maximum claim matrix.  Shape n x m.
    allocation : list[list[int]]
        Current allocation matrix.  Shape n x m.

    Raises
    ------
    InvariantViolation
        If any invariant listed in the module docstring is violated.
    """

    def __init__(
        self,
        total: List[int],
        max_claim: List[List[int]],
        allocation: List[List[int]],
    ) -> None:
        # Deep-copy inputs to prevent external mutation.
        self._total: List[int] = list(total)
        self._max: List[List[int]] = [list(row) for row in max_claim]
        self._allocation: List[List[int]] = [list(row) for row in allocation]

        # Derive dimensions.
        self._m: int = len(self._total)   # resource types
        self._n: int = len(self._max)     # processes

        # Validate inputs (order matters: dimensions first).
        self._validate_dimensions()
        self._validate_non_negativity()
        self._validate_allocation_bounds()

        # Compute derived state.
        self._need: List[List[int]] = self._compute_need()
        self._available: List[int] = self._compute_available()

        # Final conservation check.
        self._validate_conservation()

    # ── Read-Only Properties ─────────────────────────────────────────────

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
        """Total resource instances per type (copy)."""
        return list(self._total)

    @property
    def max_claim(self) -> List[List[int]]:
        """Maximum claim matrix (deep copy)."""
        return [list(row) for row in self._max]

    @property
    def allocation(self) -> List[List[int]]:
        """Current allocation matrix (deep copy)."""
        return [list(row) for row in self._allocation]

    @property
    def need(self) -> List[List[int]]:
        """Need matrix: Max - Allocation (deep copy)."""
        return [list(row) for row in self._need]

    @property
    def available(self) -> List[int]:
        """Available resource vector (copy)."""
        return list(self._available)

    # ── Pressure Metrics ─────────────────────────────────────────────────

    def resource_pressure(self) -> List[float]:
        """
        Compute per-resource pressure metrics.

            rho_j = sum_i(Need[i][j]) / Total[j]

        This is a dimensionless ratio, NOT a probability.  Values exceeding
        1.0 indicate that total outstanding demand exceeds total capacity
        for that resource type.

        Returns
        -------
        list[float]
            One pressure value per resource type.
        """
        pressures: List[float] = []
        for j in range(self._m):
            need_sum = sum(self._need[i][j] for i in range(self._n))
            pressures.append(need_sum / self._total[j])
        return pressures

    def max_pressure(self) -> float:
        """
        System bottleneck pressure: rho_max = max_j(rho_j).

        Identifies the most contended resource type.

        Returns
        -------
        float
            Maximum per-resource pressure across all resource types.
        """
        return max(self.resource_pressure())

    def pressure_report(self) -> List[Tuple[int, float]]:
        """
        Return (resource_index, rho_j) pairs sorted by pressure descending.

        Useful for identifying bottleneck resources.

        Returns
        -------
        list[tuple[int, float]]
            Sorted list of (j, rho_j) tuples.
        """
        pressures = self.resource_pressure()
        indexed = [(j, pressures[j]) for j in range(self._m)]
        indexed.sort(key=lambda pair: pair[1], reverse=True)
        return indexed

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_dimensions(self) -> None:
        """Verify dimensional consistency across all matrices and vectors."""
        if self._m == 0:
            raise InvariantViolation(
                "Total vector must have at least one resource type (m > 0)."
            )
        if self._n == 0:
            raise InvariantViolation(
                "Max matrix must have at least one process (n > 0)."
            )
        if len(self._allocation) != self._n:
            raise InvariantViolation(
                f"Allocation has {len(self._allocation)} rows; "
                f"expected {self._n} (matching Max)."
            )
        for i, row in enumerate(self._max):
            if len(row) != self._m:
                raise InvariantViolation(
                    f"Max[{i}] has {len(row)} columns; expected {self._m}."
                )
        for i, row in enumerate(self._allocation):
            if len(row) != self._m:
                raise InvariantViolation(
                    f"Allocation[{i}] has {len(row)} columns; expected {self._m}."
                )

    def _validate_non_negativity(self) -> None:
        """Verify all entries are non-negative and Total > 0."""
        for j in range(self._m):
            if not isinstance(self._total[j], int):
                raise InvariantViolation(
                    f"Total[{j}] = {self._total[j]!r} is not an integer."
                )
            if self._total[j] <= 0:
                raise InvariantViolation(
                    f"Total[{j}] = {self._total[j]}; "
                    f"each resource type must have at least one instance."
                )
        for i in range(self._n):
            for j in range(self._m):
                if not isinstance(self._max[i][j], int):
                    raise InvariantViolation(
                        f"Max[{i}][{j}] = {self._max[i][j]!r} is not an integer."
                    )
                if self._max[i][j] < 0:
                    raise InvariantViolation(
                        f"Max[{i}][{j}] = {self._max[i][j]} < 0."
                    )
                if not isinstance(self._allocation[i][j], int):
                    raise InvariantViolation(
                        f"Allocation[{i}][{j}] = {self._allocation[i][j]!r} "
                        f"is not an integer."
                    )
                if self._allocation[i][j] < 0:
                    raise InvariantViolation(
                        f"Allocation[{i}][{j}] = {self._allocation[i][j]} < 0."
                    )

    def _validate_allocation_bounds(self) -> None:
        """Verify Allocation[i][j] <= Max[i][j] for all i, j."""
        for i in range(self._n):
            for j in range(self._m):
                if self._allocation[i][j] > self._max[i][j]:
                    raise InvariantViolation(
                        f"Allocation[{i}][{j}] = {self._allocation[i][j]} > "
                        f"Max[{i}][{j}] = {self._max[i][j]}."
                    )

    def _compute_need(self) -> List[List[int]]:
        """Compute Need[i][j] = Max[i][j] - Allocation[i][j]."""
        return [
            [self._max[i][j] - self._allocation[i][j] for j in range(self._m)]
            for i in range(self._n)
        ]

    def _compute_available(self) -> List[int]:
        """Compute Available[j] = Total[j] - sum_i(Allocation[i][j])."""
        available = list(self._total)
        for i in range(self._n):
            for j in range(self._m):
                available[j] -= self._allocation[i][j]
        return available

    def _validate_conservation(self) -> None:
        """
        Verify resource conservation law and non-negative availability.

        Available[j] + sum_i(Allocation[i][j]) = Total[j]   for all j.
        Available[j] >= 0                                     for all j.
        """
        for j in range(self._m):
            alloc_sum = sum(self._allocation[i][j] for i in range(self._n))
            computed = self._available[j] + alloc_sum
            if computed != self._total[j]:
                raise InvariantViolation(
                    f"Conservation violated for resource {j}: "
                    f"Available[{j}]={self._available[j]} + "
                    f"sum(Allocation[][{j}])={alloc_sum} = {computed} "
                    f"!= Total[{j}]={self._total[j]}."
                )
            if self._available[j] < 0:
                raise InvariantViolation(
                    f"Over-allocation for resource {j}: "
                    f"sum(Allocation[][{j}])={alloc_sum} exceeds "
                    f"Total[{j}]={self._total[j]}, "
                    f"yielding Available[{j}]={self._available[j]} < 0."
                )

    # ── Display ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SystemState(n={self._n}, m={self._m}, "
            f"Total={self._total}, Available={self._available})"
        )

    def format_matrices(self) -> str:
        """
        Return a human-readable formatted string of all matrices.

        Suitable for logging, debugging, and inclusion in experiment traces.
        """
        header = f"System State: {self._n} processes, {self._m} resource types"
        lines = [
            header,
            "=" * len(header),
            f"Total:     {self._total}",
            f"Available: {self._available}",
            "",
        ]

        # Column header
        col_hdr = "         " + "  ".join(f"R{j:>2}" for j in range(self._m))
        lines.append(col_hdr)

        lines.append("Allocation:")
        for i in range(self._n):
            lines.append(f"  P{i:<3}: {self._allocation[i]}")

        lines.append("Max:")
        for i in range(self._n):
            lines.append(f"  P{i:<3}: {self._max[i]}")

        lines.append("Need (Max - Allocation):")
        for i in range(self._n):
            lines.append(f"  P{i:<3}: {self._need[i]}")

        pressures = self.resource_pressure()
        lines.append("")
        lines.append(
            f"Per-Resource Pressure (rho_j): "
            f"{[round(p, 4) for p in pressures]}"
        )
        lines.append(
            f"Bottleneck Pressure (rho_max): {round(self.max_pressure(), 4)}"
        )

        return "\n".join(lines)

