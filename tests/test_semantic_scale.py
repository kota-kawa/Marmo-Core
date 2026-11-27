"""The semantic relevance scale must be monotonic in cosine similarity."""

from __future__ import annotations

import io
import unittest
from unittest import mock

from marmo_core import (
    EmbeddingProvider,
    HybridRetriever,
    OpenAICompatibleEmbeddingProvider,
    ResourceDefinition,
    ResourceRegistry,
    SearchQuery,
)
from marmo_core.errors import ProviderError
from marmo_core.semantic import _cosine_01, _post_json
from marmo_core.vector_index import VectorIndex


class SemanticScaleTests(unittest.TestCase):
    def test_semantic_relevance_is_monotonic_in_cosine(self) -> None:
        # A negative cosine must never outscore a positive one.
        negative = _cosine_01([1.0, 0.0], [-0.6, 0.8])
        small_positive = _cosine_01([1.0, 0.0], [0.14, 0.99])
        self.assertLessEqual(negative, small_positive)
        self.assertEqual(negative, 0.0)


def _resource(resource_id: str, kind: str, description: str) -> ResourceDefinition:
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": kind,
            "name": resource_id,
            "version": "1.0.0",
            "description": description,
            "capabilities": [],
            "input_summary": "in",
            "output_summary": "out",
            "required_permissions": [],
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "core",
            "ref": f"{kind}://{resource_id}",
            "tags": [],
            **({"input_schema": {"type": "object", "properties": {}}} if kind == "tool" else {}),
            **({"instructions": ["steps"]} if kind == "skill" else {}),
        }
    )


class _Directions(EmbeddingProvider):
    """The goal and the Skills point one way; the Tool a little further away."""

    def embed(self, texts):
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        if "quokka" in text:
            return [1.0, 0.0]
        if "skillnote" in text:
            return [0.99, 0.1]
        return [0.7, 0.7]


class _ListIndex(VectorIndex):
    """A pure-Python vector index, so the test needs no numpy."""

    def build(self, ids, vectors) -> None:
        self.rows = [(identity, list(vector)) for identity, vector in zip(ids, vectors)]

    def _cosine(self, query, vector) -> float:
        norm = (sum(a * a for a in query) * sum(b * b for b in vector)) ** 0.5
        return sum(a * b for a, b in zip(query, vector)) / norm

    def nearest(self, query, k, *, exclude=()):
        scored = [(identity, self._cosine(query, vector)) for identity, vector in self.rows if identity not in exclude]
        return sorted(scored, key=lambda item: (-item[1], item[0]))[:k]

    def similarity(self, query, ids):
        return {identity: self._cosine(query, vector) for identity, vector in self.rows if identity in ids}


class HybridKindFilterTests(unittest.TestCase):
    """Neighbors of another kind must not use up the slots for the kind that was asked for."""

    def setUp(self) -> None:
        self.registry = ResourceRegistry()
        for number in range(4):
            self.registry.add(_resource(f"skill.test.note{number}", "skill", "skillnote procedure"))
        self.registry.add(_resource("tool.test.reader", "tool", "toolnote reader"))

    def _search(self, **options) -> list[str]:
        retriever = HybridRetriever(_Directions(), candidate_pool=2, **options)
        # No resource shares a word with the goal, so every candidate is a neighbor.
        results = retriever.search(self.registry, SearchQuery(task="quokka", kinds=("tool",), top_k=5))
        return [result.resource.metadata.id for result in results]

    def test_nearest_neighbors_reach_a_tool_behind_nearer_skills(self) -> None:
        self.assertEqual(self._search(), ["tool.test.reader"])

    def test_nearest_neighbors_reach_a_tool_behind_nearer_skills_with_a_vector_index(self) -> None:
        self.assertEqual(self._search(vector_index=_ListIndex), ["tool.test.reader"])

    def test_an_unfiltered_search_still_takes_only_the_candidate_pool_of_neighbors(self) -> None:
        retriever = HybridRetriever(_Directions(), candidate_pool=2)
        results = retriever.search(self.registry, SearchQuery(task="quokka", top_k=5))
        self.assertEqual(len(results), 2)
        self.assertNotIn("tool.test.reader", [result.resource.metadata.id for result in results])


class _Response(io.BytesIO):
    """What ``urlopen`` returns for a 200: a context manager over the body."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


class EmbeddingResponseTests(unittest.TestCase):
    """A 200 reply that is not the documented embeddings payload is a ProviderError."""

    def _provider(self, response) -> OpenAICompatibleEmbeddingProvider:
        return OpenAICompatibleEmbeddingProvider(
            "m", api_key="k", base_url="http://localhost/v1", transport=lambda *args: response
        )

    def test_well_formed_response_is_read_in_index_order(self) -> None:
        provider = self._provider(
            {"data": [{"index": 1, "embedding": [0, 2]}, {"index": 0, "embedding": [1, 0.5]}]}
        )
        self.assertEqual(provider.embed(["a", "b"]), [[1.0, 0.5], [0.0, 2.0]])

    def test_unexpected_wire_shapes_raise_provider_error(self) -> None:
        for label, response in {
            "not a mapping": ["embedding"],
            "no data": {"object": "list"},
            "data is not a list": {"data": "oops"},
            "wrong count": {"data": [{"embedding": [1.0]}]},
            "item without embedding": {"data": [{"index": 0}, {"index": 1}]},
            "item is not a mapping": {"data": [1, 2]},
            "non-numeric vector": {"data": [{"embedding": ["x"]}, {"embedding": [1.0]}]},
            "vector is not a list": {"data": [{"embedding": None}, {"embedding": [1.0]}]},
        }.items():
            with self.subTest(label), self.assertRaises(ProviderError):
                self._provider(response).embed(["a", "b"])

    def test_non_json_body_with_status_200_raises_provider_error(self) -> None:
        for label, body in {
            "html gateway page": b"<html><body>Bad gateway</body></html>",
            "empty": b"",
            "json that is not an object": b"[1, 2]",
            "not utf-8": b"\xff\xfe",
        }.items():
            with self.subTest(label), mock.patch(
                "marmo_core.semantic.urllib.request.urlopen", return_value=_Response(body)
            ):
                with self.assertRaises(ProviderError):
                    _post_json("http://localhost/v1/embeddings", {}, {}, 1.0)

    def test_json_object_body_is_returned(self) -> None:
        with mock.patch(
            "marmo_core.semantic.urllib.request.urlopen", return_value=_Response(b'{"data": []}')
        ):
            self.assertEqual(_post_json("http://localhost/v1/embeddings", {}, {}, 1.0), {"data": []})


if __name__ == "__main__":
    unittest.main()
