import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab import stats
from agentmeasure_lab.rng import DetRng, balanced_variant_sequence


class TestRng(unittest.TestCase):
    def test_same_stream_parts_same_sequence(self):
        a = DetRng(42, "exp", "task-1", "v", 1)
        b = DetRng(42, "exp", "task-1", "v", 1)
        self.assertEqual([a.random() for _ in range(50)], [b.random() for _ in range(50)])

    def test_different_stream_parts_diverge(self):
        a = DetRng(42, "exp", "task-1", "v", 1)
        b = DetRng(42, "exp", "task-2", "v", 1)
        self.assertNotEqual([a.random() for _ in range(10)], [b.random() for _ in range(10)])

    def test_bernoulli_frequency(self):
        rng = DetRng(1, "freq")
        draws = [rng.bernoulli(0.3) for _ in range(10000)]
        self.assertAlmostEqual(sum(draws) / 10000, 0.3, delta=0.02)

    def test_balanced_assignment_is_balanced(self):
        rng = DetRng(9, "balance")
        seq = balanced_variant_sequence(101, ["a", "b", "c"], rng)
        counts = {v: seq.count(v) for v in ("a", "b", "c")}
        self.assertEqual(sum(counts.values()), 101)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)


class TestStats(unittest.TestCase):
    def test_wilson_contains_point_and_shrinks(self):
        wide = stats.wilson_interval(5, 10)
        narrow = stats.wilson_interval(500, 1000)
        for lo, hi in (wide, narrow):
            self.assertLessEqual(lo, 0.5)
            self.assertLessEqual(0.5, hi)
        self.assertLess(narrow[1] - narrow[0], wide[1] - wide[0])

    def test_wilson_zero_success(self):
        lo, hi = stats.wilson_interval(0, 20)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_significant_difference_detected(self):
        z, p = stats.two_proportion_z_test(100, 400, 160, 400)
        self.assertLess(p, 0.01)

    def test_no_difference_high_p(self):
        z, p = stats.two_proportion_z_test(200, 400, 198, 400)
        self.assertGreater(p, 0.5)

    def test_newcombe_ci_excludes_zero_when_significant(self):
        lo, hi = stats.newcombe_diff_interval(100, 400, 160, 400)
        self.assertGreater(lo, 0.0)

    def test_required_n_reasonable(self):
        n = stats.required_n_per_arm(0.30, 0.40)
        self.assertGreater(n, 100)
        self.assertLess(n, 2000)

    def test_median(self):
        self.assertEqual(stats.median([1, 2, 3]), 2.0)
        self.assertEqual(stats.median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(stats.median([]))


if __name__ == "__main__":
    unittest.main()
