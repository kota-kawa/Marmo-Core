"""The semantic relevance scale must be monotonic in cosine similarity."""

from __future__ import annotations

import unittest

from marmo_core.semantic import _cosine_01


class SemanticScaleTests(unittest.TestCase):
    def test_semantic_relevance_is_monotonic_in_cosine(self) -> None:
        # cos = -0.6 must not outscore cos = +0.6 (an earlier mapping gave 0.2 vs 0.6
        # for these, and 0.43 vs 0.14 for -0.14 vs +0.14).
        negative = _cosine_01([1.0, 0.0], [-0.6, 0.8])
        small_positive = _cosine_01([1.0, 0.0], [0.14, 0.99])
        self.assertLessEqual(negative, small_positive)
        self.assertEqual(negative, 0.0)


if __name__ == "__main__":
    unittest.main()
