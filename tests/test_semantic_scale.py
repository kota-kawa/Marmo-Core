"""The semantic relevance scale must be monotonic in cosine similarity."""

from __future__ import annotations

import unittest

from marmo_core.semantic import _cosine_01


class SemanticScaleTests(unittest.TestCase):
    def test_semantic_relevance_is_monotonic_in_cosine(self) -> None:
        # A negative cosine must never outscore a positive one.
        negative = _cosine_01([1.0, 0.0], [-0.6, 0.8])
        small_positive = _cosine_01([1.0, 0.0], [0.14, 0.99])
        self.assertLessEqual(negative, small_positive)
        self.assertEqual(negative, 0.0)


if __name__ == "__main__":
    unittest.main()
