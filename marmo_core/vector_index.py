"""Vector indexes for the semantic half of ``HybridRetriever``.

By default ``HybridRetriever`` scores the query against every document
vector in pure Python, which keeps the core free of dependencies but costs
hundreds of milliseconds per query at ten thousand resources. A
``VectorIndex`` replaces that loop:

- ``ExactVectorIndex`` computes the same cosine similarities with one numpy
  matrix product (exact; numpy ships with the ``benchmark`` extra).
- ``HNSWVectorIndex`` answers nearest-neighbor queries approximately with a
  usearch HNSW graph (``benchmark-ann`` extra). Similarities for the
  lexical candidates are still computed exactly.

Both report cosine similarity in [-1, 1]; ``HybridRetriever`` maps it to its
relevance scale exactly as the pure-Python path does.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Collection, Sequence


class VectorIndex(ABC):
    """Nearest-neighbor search over one catalog's document vectors."""

    @abstractmethod
    def build(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        """Index ``vectors`` under ``ids`` (replacing any previous content)."""

    @abstractmethod
    def nearest(self, query: Sequence[float], k: int, *, exclude: Collection[str] = ()) -> list[tuple[str, float]]:
        """Up to ``k`` (id, cosine) pairs, most similar first, skipping ``exclude``."""

    @abstractmethod
    def similarity(self, query: Sequence[float], ids: Collection[str]) -> dict[str, float]:
        """Exact cosine similarity of ``query`` to each indexed id in ``ids``."""


def _numpy() -> Any:
    try:
        import numpy  # type: ignore[import-not-found]  # Optional vectorization dependency.
    except ImportError as error:  # pragma: no cover - exercised only without numpy
        raise ImportError("vector indexes need numpy: pip install 'marmo-core[benchmark]'") from error
    return numpy


class _NormalizedMatrix:
    """Row-normalized document matrix shared by both indexes."""

    def __init__(self) -> None:
        self.np = _numpy()
        self.ids: list[str] = []
        self.position: dict[str, int] = {}
        self.matrix: Any = None

    def load(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        np = self.np
        self.ids = list(ids)
        self.position = {identity: index for index, identity in enumerate(self.ids)}
        if not self.ids:
            self.matrix = None  # an empty catalog: every query finds nothing
            return
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(self.ids):
            raise ValueError("vectors must be a non-empty 2-D array with one row per id")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        self.matrix = matrix / norms

    def normalized_query(self, query: Sequence[float]) -> Any:
        np = self.np
        vector = np.asarray(query, dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm else vector

    def similarity(self, query: Sequence[float], ids: Collection[str]) -> dict[str, float]:
        positions = [(identity, self.position[identity]) for identity in ids if identity in self.position]
        if not positions or self.matrix is None:
            return {}
        q = self.normalized_query(query)
        rows = self.matrix[[position for _, position in positions]]
        values = rows @ q
        return {identity: float(value) for (identity, _), value in zip(positions, values)}


class ExactVectorIndex(VectorIndex):
    """Exact cosine search with one numpy matrix product per query."""

    def __init__(self) -> None:
        self._data = _NormalizedMatrix()

    def build(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        self._data.load(ids, vectors)

    def nearest(self, query: Sequence[float], k: int, *, exclude: Collection[str] = ()) -> list[tuple[str, float]]:
        data = self._data
        if data.matrix is None or k <= 0:
            return []
        np = data.np
        scores = data.matrix @ data.normalized_query(query)
        excluded = [data.position[identity] for identity in exclude if identity in data.position]
        if excluded:
            scores = scores.copy()
            scores[excluded] = -np.inf
        take = min(k, len(data.ids) - len(excluded))
        if take <= 0:
            return []
        top = np.argpartition(-scores, take - 1)[:take]
        ordered = sorted(top.tolist(), key=lambda index: (-float(scores[index]), data.ids[index]))
        return [(data.ids[index], float(scores[index])) for index in ordered]

    def similarity(self, query: Sequence[float], ids: Collection[str]) -> dict[str, float]:
        return self._data.similarity(query, ids)


class HNSWVectorIndex(VectorIndex):
    """Approximate nearest neighbors with a usearch HNSW graph.

    ``connectivity`` is HNSW's M, ``expansion_add`` / ``expansion_search``
    its efConstruction / ef. Exact similarities for named ids (the lexical
    candidates) come from the normalized matrix kept alongside the graph.
    """

    def __init__(self, *, connectivity: int = 16, expansion_add: int = 128, expansion_search: int = 64) -> None:
        self.connectivity = connectivity
        self.expansion_add = expansion_add
        self.expansion_search = expansion_search
        self._data = _NormalizedMatrix()
        self._index: Any = None

    def build(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        try:
            from usearch.index import Index  # type: ignore[import-not-found]  # Optional ANN dependency.
        except ImportError as error:  # pragma: no cover - exercised only without usearch
            raise ImportError("HNSWVectorIndex needs usearch: pip install 'marmo-core[benchmark-ann]'") from error
        data = self._data
        data.load(ids, vectors)
        if data.matrix is None:
            self._index = None
            return
        np = data.np
        index = Index(
            ndim=int(data.matrix.shape[1]),
            metric="cos",
            connectivity=self.connectivity,
            expansion_add=self.expansion_add,
            expansion_search=self.expansion_search,
        )
        index.add(np.arange(len(data.ids), dtype=np.uint64), data.matrix)
        self._index = index

    def nearest(self, query: Sequence[float], k: int, *, exclude: Collection[str] = ()) -> list[tuple[str, float]]:
        data = self._data
        if self._index is None or k <= 0:
            return []
        excluded = set(exclude)
        wanted = min(len(data.ids), k + len(excluded))
        matches = self._index.search(data.normalized_query(query), wanted)
        found: list[tuple[str, float]] = []
        for key, distance in zip(matches.keys.tolist(), matches.distances.tolist()):
            identity = data.ids[int(key)]
            if identity in excluded:
                continue
            found.append((identity, 1.0 - float(distance)))
            if len(found) >= k:
                break
        return found

    def similarity(self, query: Sequence[float], ids: Collection[str]) -> dict[str, float]:
        return self._data.similarity(query, ids)
