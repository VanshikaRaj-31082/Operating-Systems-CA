"""
Unit Tests for Data Models and Invariant Enforcement (src/models.py).
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import (
    SystemState,
    DimensionMismatchError,
    InvalidValueError,
    ResourceConservationError,
)


class TestSystemStateModels(unittest.TestCase):
    """Test suite for SystemState invariants, validation, and immutability."""

    def test_valid_state_construction(self):
        """Test creating a valid SystemState with computed Available."""
        state = SystemState(
            total=[10, 5, 7],
            allocation=[
                [2, 1, 1],
                [3, 2, 2],
            ],
            request=[
                [1, 0, 2],
                [0, 1, 1],
            ],
        )
        self.assertEqual(state.n, 2)
        self.assertEqual(state.m, 3)
        self.assertEqual(state.total, [10, 5, 7])
        self.assertEqual(state.allocation, [[2, 1, 1], [3, 2, 2]])
        self.assertEqual(state.request, [[1, 0, 2], [0, 1, 1]])
        # Available should be [10 - 5, 5 - 3, 7 - 3] = [5, 2, 4]
        self.assertEqual(state.available, [5, 2, 4])
        self.assertFalse(state.is_single_instance)

    def test_valid_state_with_explicit_available(self):
        """Test creating a valid SystemState with explicit valid Available vector."""
        state = SystemState(
            total=[5, 5],
            allocation=[
                [2, 3],
                [1, 1],
            ],
            request=[
                [0, 1],
                [1, 0],
            ],
            available=[2, 1],
        )
        self.assertEqual(state.available, [2, 1])

    def test_single_instance_flag(self):
        """Test that is_single_instance returns True when all Total == 1."""
        single_state = SystemState(
            total=[1, 1, 1],
            allocation=[[1, 0, 0], [0, 1, 0]],
            request=[[0, 1, 0], [0, 0, 1]],
        )
        self.assertTrue(single_state.is_single_instance)

        multi_state = SystemState(
            total=[1, 2, 1],
            allocation=[[1, 0, 0], [0, 1, 0]],
            request=[[0, 1, 0], [0, 0, 1]],
        )
        self.assertFalse(multi_state.is_single_instance)

    def test_negative_values_rejected(self):
        """Test that negative values in any vector/matrix raise InvalidValueError."""
        # Negative Total
        with self.assertRaises(InvalidValueError):
            SystemState(total=[-1, 2], allocation=[[0, 0]], request=[[0, 0]])

        # Zero Total (Total must be >= 1)
        with self.assertRaises(InvalidValueError):
            SystemState(total=[0, 2], allocation=[[0, 0]], request=[[0, 0]])

        # Negative Allocation
        with self.assertRaises(InvalidValueError):
            SystemState(total=[2, 2], allocation=[[-1, 0]], request=[[0, 0]])

        # Negative Request
        with self.assertRaises(InvalidValueError):
            SystemState(total=[2, 2], allocation=[[1, 0]], request=[[0, -1]])

        # Negative Available
        with self.assertRaises(InvalidValueError):
            SystemState(total=[2, 2], allocation=[[1, 0]], request=[[0, 0]], available=[-1, 2])

    def test_non_integer_values_rejected(self):
        """Test that non-integer types (floats, strings, bools) are rejected."""
        with self.assertRaises(InvalidValueError):
            SystemState(total=[2.5, 2], allocation=[[0, 0]], request=[[0, 0]])  # type: ignore

        with self.assertRaises(InvalidValueError):
            SystemState(total=[True, 2], allocation=[[0, 0]], request=[[0, 0]])  # type: ignore

    def test_dimension_mismatch_detected(self):
        """Test that ragged or dimensionally inconsistent inputs raise DimensionMismatchError."""
        # Request row count != Allocation row count
        with self.assertRaises(DimensionMismatchError):
            SystemState(
                total=[3, 3],
                allocation=[[1, 1], [1, 1]],
                request=[[0, 0]],  # Only 1 row for 2 processes
            )

        # Allocation column count != Total length
        with self.assertRaises(DimensionMismatchError):
            SystemState(
                total=[3, 3],
                allocation=[[1, 1, 1]],  # 3 cols instead of 2
                request=[[0, 0]],
            )

        # Request column count != Total length
        with self.assertRaises(DimensionMismatchError):
            SystemState(
                total=[3, 3],
                allocation=[[1, 1]],
                request=[[0, 0, 0]],
            )

        # Available length != Total length
        with self.assertRaises(DimensionMismatchError):
            SystemState(
                total=[3, 3],
                allocation=[[1, 1]],
                request=[[0, 0]],
                available=[2],  # Length 1 instead of 2
            )

    def test_conservation_violation_raises(self):
        """Test that over-allocation or mismatched Available raises ResourceConservationError."""
        # Over-allocated (allocated 4 of resource 0 when total is only 3)
        with self.assertRaises(ResourceConservationError):
            SystemState(
                total=[3, 3],
                allocation=[[2, 1], [2, 1]],
                request=[[0, 0], [0, 0]],
            )

        # Explicit Available does not add up to Total
        with self.assertRaises(ResourceConservationError):
            SystemState(
                total=[5, 5],
                allocation=[[2, 2]],
                request=[[0, 0]],
                available=[4, 3],  # 4 + 2 = 6 != 5
            )

    def test_immutability_and_deep_copying(self):
        """Test that modifying properties externally does not corrupt SystemState."""
        total = [5, 5]
        alloc = [[1, 2]]
        req = [[0, 1]]

        state = SystemState(total=total, allocation=alloc, request=req)

        # Mutate external source lists
        total[0] = 999
        alloc[0][0] = 888
        req[0][0] = 777

        self.assertEqual(state.total, [5, 5])
        self.assertEqual(state.allocation, [[1, 2]])
        self.assertEqual(state.request, [[0, 1]])

        # Mutate list returned by property
        state.total[0] = 111
        state.allocation[0][0] = 222
        state.request[0][0] = 333
        state.available[0] = 444

        self.assertEqual(state.total, [5, 5])
        self.assertEqual(state.allocation, [[1, 2]])
        self.assertEqual(state.request, [[0, 1]])
        self.assertEqual(state.available, [4, 3])

    def test_custom_process_and_resource_labels(self):
        """Test custom process and resource names with validation."""
        state = SystemState(
            total=[1, 1],
            allocation=[[1, 0]],
            request=[[0, 1]],
            process_names=["Worker-Alpha"],
            resource_names=["Mutex-A", "Mutex-B"],
        )
        self.assertEqual(state.process_names, ["Worker-Alpha"])
        self.assertEqual(state.resource_names, ["Mutex-A", "Mutex-B"])

        # Name count mismatch
        with self.assertRaises(DimensionMismatchError):
            SystemState(
                total=[1, 1],
                allocation=[[1, 0]],
                request=[[0, 1]],
                process_names=["P0", "P1"],  # 2 names for 1 process
            )

    def test_equality_and_serialization(self):
        """Test __eq__ and to_dict functionality."""
        state1 = SystemState(total=[2, 2], allocation=[[1, 1]], request=[[0, 0]])
        state2 = SystemState(total=[2, 2], allocation=[[1, 1]], request=[[0, 0]])
        state3 = SystemState(total=[2, 2], allocation=[[0, 1]], request=[[0, 0]])

        self.assertEqual(state1, state2)
        self.assertNotEqual(state1, state3)

        d = state1.to_dict()
        self.assertEqual(d["n"], 1)
        self.assertEqual(d["m"], 2)
        self.assertEqual(d["available"], [1, 1])


if __name__ == "__main__":
    unittest.main()
