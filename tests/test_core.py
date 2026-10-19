import unittest

from tiny_count_min_sketch import CountMinSketch


class TestCountMinSketch(unittest.TestCase):
    def test_add_and_query_single_item(self):
        sketch = CountMinSketch(width=10, depth=3)
        sketch.add("apple")
        self.assertEqual(sketch.query("apple"), 1)

    def test_query_missing_item_is_zero(self):
        sketch = CountMinSketch(width=10, depth=3)
        self.assertEqual(sketch.query("nothing"), 0)

    def test_add_count_greater_than_one(self):
        sketch = CountMinSketch(width=50, depth=5)
        sketch.add("item", 7)
        self.assertEqual(sketch.query("item"), 7)

    def test_overestimate_never_underestimate(self):
        """With many distinct items packed into a small table, query must
        still be at least the true count for a repeatedly added item."""
        sketch = CountMinSketch(width=4, depth=3)
        for i in range(100):
            sketch.add(f"item_{i}")
        for _ in range(10):
            sketch.add("target")
        self.assertGreaterEqual(sketch.query("target"), 10)

    def test_add_bytes_and_str_treated_consistently(self):
        sketch = CountMinSketch(width=20, depth=3)
        sketch.add("key")
        sketch.add(b"key")
        self.assertEqual(sketch.query("key"), 2)
        self.assertEqual(sketch.query(b"key"), 2)

    def test_negative_count_clamped_to_zero(self):
        """Decrementing below zero clamps each counter at zero so the
        never-underestimate invariant survives."""
        sketch = CountMinSketch(width=10, depth=3)
        sketch.add("x", 5)
        sketch.add("x", -10)
        self.assertEqual(sketch.query("x"), 0)

    def test_negative_count_partial_decrement(self):
        sketch = CountMinSketch(width=10, depth=3)
        sketch.add("x", 5)
        sketch.add("x", -2)
        self.assertEqual(sketch.query("x"), 3)

    def test_total_reflects_all_adds(self):
        sketch = CountMinSketch(width=10, depth=3)
        sketch.add("a", 3)
        sketch.add("b", 4)
        sketch.add("c")
        self.assertEqual(sketch.total, 8)

    def test_merge_combines_counts(self):
        a = CountMinSketch(width=20, depth=3)
        b = CountMinSketch(width=20, depth=3)
        a.add("x", 5)
        b.add("x", 3)
        a.merge(b)
        self.assertGreaterEqual(a.query("x"), 8)

    def test_merge_dimension_mismatch_raises(self):
        a = CountMinSketch(width=20, depth=3)
        b = CountMinSketch(width=10, depth=3)
        with self.assertRaises(ValueError):
            a.merge(b)

    def test_reset_clears_all_counters(self):
        sketch = CountMinSketch(width=10, depth=3)
        sketch.add("x", 5)
        sketch.add("y")
        sketch.reset()
        self.assertEqual(sketch.query("x"), 0)
        self.assertEqual(sketch.query("y"), 0)
        self.assertEqual(sketch.total, 0)

    def test_invalid_width_raises(self):
        with self.assertRaises(ValueError):
            CountMinSketch(width=0, depth=3)
        with self.assertRaises(ValueError):
            CountMinSketch(width=-5, depth=3)

    def test_invalid_depth_raises(self):
        with self.assertRaises(ValueError):
            CountMinSketch(width=10, depth=0)
        with self.assertRaises(ValueError):
            CountMinSketch(width=10, depth=-1)

    def test_non_int_dimensions_raise_type_error(self):
        with self.assertRaises(TypeError):
            CountMinSketch(width=3.5, depth=3)
        with self.assertRaises(TypeError):
            CountMinSketch(width=10, depth="3")

    def test_bool_dimension_raises_type_error(self):
        with self.assertRaises(TypeError):
            CountMinSketch(width=True, depth=3)
        with self.assertRaises(TypeError):
            CountMinSketch(width=10, depth=False)

    def test_custom_hash_func_deterministic(self):
        """Inject a trivial hash function so indices are predictable."""
        def fake_hash(data: bytes) -> int:
            # Use the byte-sum so different salts still differ.
            return sum(data)

        sketch = CountMinSketch(width=100, depth=3, hash_func=fake_hash)
        sketch.add("item")
        self.assertEqual(sketch.query("item"), 1)
        # Without the salt, indices would collide across rows; with the
        # per-row salt, rows 0, 1, 2 get different column positions.
        # This test just confirms the wiring works end-to-end.

    def test_count_must_be_int(self):
        sketch = CountMinSketch(width=10, depth=3)
        with self.assertRaises(TypeError):
            sketch.add("x", 1.0)
        with self.assertRaises(TypeError):
            sketch.add("x", True)


if __name__ == "__main__":
    unittest.main()
