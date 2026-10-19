from __future__ import annotations

import hashlib
from typing import Callable, Iterable, Optional, Union, overload


class CountMinSketch:
    """A Count-Min Sketch for estimating item frequencies in a data stream.

    The sketch uses multiple hash functions to index into a 2D table of
    counters. Each ``add`` increments one counter per row; each ``query``
    returns the minimum across all rows for that item. The minimum is an
    upper bound on the true frequency — never an underestimate — and the
    expected over-count is bounded by ``(m / width)`` where ``m`` is total
    items added.

    The hash functions are derived by salting a single SHA-256 digest with
    a per-row string. This avoids a dependency on a fast non-cryptographic
    hash (which the standard library does not ship) while remaining
    deterministic and portable. SHA-256 is overkill for distribution quality,
    but it is always available in CPython and introduces no third-party code.
    """

    def __init__(
        self,
        width: int,
        depth: int,
        hash_func: Optional[Callable[[bytes], int]] = None,
    ) -> None:
        """Create a sketch with ``depth`` rows and ``width`` counters per row.

        Args:
            width: Number of counters in each row. Must be positive.
            depth: Number of independent hash functions (rows). Must be
                positive. Larger ``depth`` reduces the probability of a large
                over-estimate; larger ``width`` reduces the magnitude of the
                worst-case over-estimate.
            hash_func: Optional callable that accepts ``bytes`` and returns
                an ``int``. If omitted, SHA-256 is used. This argument exists
                primarily so tests can inject a deterministic hash instead of
                relying on the default cryptographic digest.

        Raises:
            ValueError: If ``width`` or ``depth`` is not positive.
            TypeError: If ``width`` or ``depth`` is not an ``int``.
        """
        if not isinstance(width, int) or isinstance(width, bool):
            raise TypeError("width must be an int")
        if not isinstance(depth, int) or isinstance(depth, bool):
            raise TypeError("depth must be an int")
        if width <= 0:
            raise ValueError("width must be positive")
        if depth <= 0:
            raise ValueError("depth must be positive")

        self._width = width
        self._depth = depth
        self._table: list[list[int]] = [
            [0] * width for _ in range(depth)
        ]
        self._total = 0

        if hash_func is None:
            self._hash_func: Callable[[bytes], int] = self._sha256_to_int
        else:
            self._hash_func = hash_func

    @staticmethod
    def _sha256_to_int(data: bytes) -> int:
        """Hash ``data`` with SHA-256 and return the digest as a big integer."""
        return int.from_bytes(hashlib.sha256(data).digest(), "big")

    def _indices(self, key: Union[str, bytes]) -> list[int]:
        """Return the column index for ``key`` in each row."""
        if isinstance(key, str):
            data = key.encode("utf-8")
        else:
            data = key

        out: list[int] = []
        for row in range(self._depth):
            salted = str(row).encode("utf-8") + data
            out.append(self._hash_func(salted) % self._width)
        return out

    def add(self, key: Union[str, bytes], count: int = 1) -> None:
        """Add ``count`` to the frequency estimate for ``key``.

        A negative ``count`` is permitted to support decrementing counters
        (e.g. when a previously added item is removed from the stream).
        Because the true count can never be negative, a negative ``count``
        is clamped so no counter drops below zero — this preserves the
        "never underestimate" invariant.

        Args:
            key: The item whose frequency to adjust.
            count: Amount to add (may be negative). Defaults to 1.

        Raises:
            TypeError: If ``count`` is not an ``int``.
        """
        if not isinstance(count, int) or isinstance(count, bool):
            raise TypeError("count must be an int")

        indices = self._indices(key)
        for row, col in enumerate(indices):
            self._table[row][col] += count
            if self._table[row][col] < 0:
                self._table[row][col] = 0
        self._total += count
        if self._total < 0:
            self._total = 0

    @overload
    def query(self, key: str) -> int:
        ...

    @overload
    def query(self, key: bytes) -> int:
        ...

    def query(self, key: Union[str, bytes]) -> int:
        """Estimate the frequency of ``key``.

        The returned value is always at least the true frequency (an
        over-estimate), never below it.
        """
        indices = self._indices(key)
        return min(self._table[row][col] for row, col in enumerate(indices))

    def merge(self, other: "CountMinSketch") -> None:
        """Point-wise add another sketch's counters into this one.

        This implements the sum operation: after merging, querying an item
        here returns approximately the sum of what it would have returned in
        each sketch.

        Args:
            other: Another sketch with identical ``width`` and ``depth``.

        Raises:
            ValueError: If the two sketches have mismatched dimensions.
        """
        if not isinstance(other, CountMinSketch):
            raise TypeError("other must be a CountMinSketch")
        if self._width != other._width or self._depth != other._depth:
            raise ValueError(
                "Cannot merge sketches with different dimensions"
            )
        for r in range(self._depth):
            row_a = self._table[r]
            row_b = other._table[r]
            for c in range(self._width):
                row_a[c] += row_b[c]
        self._total += other._total

    def reset(self) -> None:
        """Zero every counter and set the total count to zero."""
        for r in range(self._depth):
            row = self._table[r]
            for c in range(self._width):
                row[c] = 0
        self._total = 0

    @property
    def width(self) -> int:
        """Number of counters per row."""
        return self._width

    @property
    def depth(self) -> int:
        """Number of rows (hash functions)."""
        return self._depth

    @property
    def total(self) -> int:
        """Total number of items added (sum of all ``count`` arguments)."""
        return self._total
