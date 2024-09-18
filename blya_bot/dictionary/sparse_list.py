from dataclasses import dataclass
from typing import List, Optional, TypeVar, Generic

# Define a generic type variable for the value
T = TypeVar('T')

@dataclass(slots=True)
class Range(Generic[T]):
    start: int  # Inclusive start index
    end: int  # Exclusive end index
    value: T  # Value to store in the range

class SparseList(Generic[T]):
    def __init__(self) -> None:
        self.ranges: List[Range[T]] = []

    def add(self, start: int, end: int, value: T) -> None:
        """
        Adds a range [start, end) with the given value to the sparse list.
        Overlapping ranges are handled correctly, and the list maintains minimal storage.
        """
        new_ranges = []
        i = 0
        n = len(self.ranges)

        # Add ranges before the new range
        while i < n and self.ranges[i].end <= start:
            new_ranges.append(self.ranges[i])
            i += 1

        # Handle overlapping ranges
        while i < n and self.ranges[i].start < end:
            current = self.ranges[i]
            # Add non-overlapping part before the new range
            if current.start < start:
                new_ranges.append(Range(current.start, start, current.value))
            # Add non-overlapping part after the new range
            if current.end > end:
                new_ranges.append(Range(end, current.end, current.value))
            i += 1

        # Add the new range
        new_ranges.append(Range(start, end, value))

        # Add the remaining ranges after the new range
        while i < n:
            new_ranges.append(self.ranges[i])
            i += 1

        # Merge adjacent ranges with the same value
        merged_ranges: List[Range[T]] = []
        for r in sorted(new_ranges, key=lambda r: r.start):
            if merged_ranges and merged_ranges[-1].end == r.start and merged_ranges[-1].value == r.value:
                # Extend the previous range
                merged_ranges[-1].end = r.end
            else:
                merged_ranges.append(r)

        self.ranges = merged_ranges

    def __getitem__(self, k: int) -> T:
        sentinel = object()
        val = self.get(k, sentinel)
        if val is sentinel:
            raise KeyError(f"No element at index {k}")
        return val

    def get(self, idx: int, default: Optional[T] = None) -> Optional[T]:
        """
        Retrieves the value at the specified index. If the index is not covered by any range,
        returns the default value.
        """
        left = 0
        right = len(self.ranges) - 1

        # Binary search to find the range containing idx
        while left <= right:
            mid = (left + right) // 2
            r = self.ranges[mid]
            if idx < r.start:
                right = mid - 1
            elif idx >= r.end:
                left = mid + 1
            else:
                return r.value

        return default

    def as_list(self) -> List[Optional[T]]:
        """
        Converts the sparse list to a regular list, filling in None for unspecified indices.
        """
        if not self.ranges:
            return []

        max_index = max(r.end for r in self.ranges)
        result: List[Optional[T]] = [None] * max_index

        for r in self.ranges:
            result[r.start : r.end] = [r.value] * (r.end - r.start)

        # Remove trailing None values to match the actual length
        while result and result[-1] is None:
            result.pop()

        return result