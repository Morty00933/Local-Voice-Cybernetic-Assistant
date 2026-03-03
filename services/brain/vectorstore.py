from __future__ import annotations

from typing import List, Tuple, Dict, Any
import logging
import math
import threading

from .interfaces import VectorStore
from shared.config import settings

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, PointStruct, VectorParams
    _HAS_QDRANT = True
except Exception:
    QdrantClient = Any
    PointStruct = Any
    Distance = Any
    VectorParams = Any
    _HAS_QDRANT = False

logger = logging.getLogger(__name__)

_vectorstore_singleton: VectorStore | None = None
_vectorstore_lock = threading.Lock()


class InMemoryVectorStore(VectorStore):
    """Simple cosine-similarity vector store for tests and graceful fallbacks."""

    def __init__(self, dim: int):
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim
        self._store: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors and payloads lengths must match")
        with self._lock:
            for idx, vid in enumerate(ids):
                vec = vectors[idx]
                if len(vec) != self.dim:
                    raise ValueError("vector dimensionality mismatch")
                self._store[vid] = (list(vec), dict(payloads[idx] or {}))

    def search(self, query: List[float], top_k: int) -> List[Tuple[Dict[str, Any], float]]:
        if len(query) != self.dim:
            raise ValueError("query vector dimensionality mismatch")
        q_norm = math.sqrt(sum(v * v for v in query)) or 1.0
        with self._lock:
            scored: List[Tuple[Dict[str, Any], float]] = []
            for _, (vec, payload) in self._store.items():
                score = sum(q * v for q, v in zip(query, vec)) / (
                    q_norm * (math.sqrt(sum(v * v for v in vec)) or 1.0)
                )
                scored.append((dict(payload), float(score)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:max(1, top_k)]


class QdrantVS(VectorStore):
    def __init__(self, url: str, collection: str, dim: int):
        if not _HAS_QDRANT:
            raise RuntimeError("qdrant-client is unavailable")
        self.client = QdrantClient(url=url, check_compatibility=False)
        self.collection = collection
        self.dim = dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        names = {c.name for c in self.client.get_collections().collections}
        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def upsert(
        self,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> None:
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(self, query: List[float], top_k: int) -> List[Tuple[Dict[str, Any], float]]:
        limit = max(1, top_k)
        # qdrant-client >=1.12 removed .search(), use .query_points()
        if hasattr(self.client, "query_points"):
            res = self.client.query_points(
                collection_name=self.collection,
                query=query,
                limit=limit,
                with_payload=True,
            )
            return [(p.payload or {}, float(p.score)) for p in res.points]
        # qdrant-client <1.12 — legacy .search()
        res = self.client.search(
            collection_name=self.collection,
            query_vector=query,
            limit=limit,
            with_payload=True,
        )
        return [(p.payload or {}, float(p.score)) for p in res]


def _build_vectorstore() -> VectorStore:
    backend = (settings.VECTOR_BACKEND or "qdrant").lower()
    if backend in {"memory", "inmemory", "local"}:
        return InMemoryVectorStore(settings.EMBED_DIM)
    if backend == "qdrant":
        try:
            return QdrantVS(settings.QDRANT_URL, settings.QDRANT_COLLECTION, settings.EMBED_DIM)
        except Exception as exc:
            logger.warning("Falling back to InMemoryVectorStore: %s", exc)
            return InMemoryVectorStore(settings.EMBED_DIM)
    raise NotImplementedError(f"Unsupported VECTOR_BACKEND={backend}")


def get_vectorstore() -> VectorStore:
    global _vectorstore_singleton
    if _vectorstore_singleton is None:
        with _vectorstore_lock:
            if _vectorstore_singleton is None:
                _vectorstore_singleton = _build_vectorstore()
    return _vectorstore_singleton
