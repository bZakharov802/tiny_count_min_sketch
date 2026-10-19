# tiny_count_min_sketch

A pure-Python Count-Min Sketch for estimating item frequencies in a data stream using multiple hash functions.

```python
from tiny_count_min_sketch import CountMinSketch

sketch = CountMinSketch(width=1000, depth=5)

for word in ["apple", "banana", "apple", "cherry", "apple"]:
    sketch.add(word)

print(sketch.query("apple"))   # 3
print(sketch.query("cherry"))  # 1
print(sketch.total)             # 5
```

## Why this exists

When you need per-item counts from a stream too large or too fast to hold in a dictionary, a Count-Min Sketch trades exactness for constant memory. You configure it with a `width` (counters per row) and `depth` (number of rows / hash functions). Memory is `width * depth` integers. The estimate is always an over-count — never below the true frequency — and the expected error is bounded by `total_items / width`.

The library has zero dependencies beyond the standard library. Hash functions are derived by salting a single SHA-256 digest with a per-row string, which keeps the implementation portable and deterministic without pulling in a non-cryptographic hash library. SHA-256 is heavier than necessary for distribution quality, but it is always present in CPython and avoids any external dependency.

## The awkward edge

Because the estimate is an upper bound, collisions inflate counts. A small `width` with many distinct items produces large over-estimates. There is no subtraction trick here (no conservative updates), so the estimate can drift well above the true count in adversarial workloads. Negative `count` arguments to `add` are supported and clamped at zero per counter, preserving the never-underestimate property.

## Exports

- `CountMinSketch` — the only public class.
  - `CountMinSketch(width, depth, hash_func=None)` — constructor. `width` and `depth` must be positive `int`.
  - `.add(key, count=1)` — add `count` to `key`'s estimate. `key` may be `str` or `bytes`. `count` may be negative.
  - `.query(key)` — return the estimated frequency of `key`.
  - `.merge(other)` — point-wise sum another sketch of identical dimensions.
  - `.reset()` — zero all counters.
  - `.width`, `.depth`, `.total` — read-only properties.
