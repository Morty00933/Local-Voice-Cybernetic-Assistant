from __future__ import annotations

from typing import List, Optional, Tuple
import hashlib
import json
import math
import logging
import os
import threading
from collections import OrderedDict

import httpx

from .interfaces import Embeddings
from shared.config import settings

logger = logging.getLogger(__name__)

_embeddings_singleton: Embeddings | None = None
_embeddings_lock = threading.Lock()

# ── Embedding cache ─────────────────────────────────────────────

_CACHE_MAX = int(os.environ.get("EMBED_CACHE_MAX", "4096"))


class _EmbedCache:
    """Thread-safe LRU cache for embedding vectors.

    L1: in-memory OrderedDict (fast).
    L2: Redis (persistent, shared across restarts) — optional.
    """

    def __init__(self, maxsize: int = _CACHE_MAX):
        self._maxsize = maxsize
        self._lru: OrderedDict[str, List[float]] = OrderedDict()
        self._lock = threading.Lock()
        self._redis = None
        self._hits = 0
        self._misses = 0
        self._init_redis()

    def _init_redis(self) -> None:
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            return
        try:
            import redis as _redis
            self._redis = _redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            logger.info("Embedding cache: Redis L2 connected")
        except Exception as exc:
            logger.warning("Embedding cache: Redis unavailable (%s), memory-only", exc)
            self._redis = None

    @staticmethod
    def _key(text: str) -> str:
        return "emb:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def get(self, text: str) -> Optional[List[float]]:
        key = self._key(text)
        # L1
        with self._lock:
            if key in self._lru:
                self._lru.move_to_end(key)
                self._hits += 1
                return self._lru[key]
        # L2
        if self._redis:
            try:
                raw = self._redis.get(key)
                if raw:
                    vec = json.loads(raw)
                    with self._lock:
                        self._lru[key] = vec
                        if len(self._lru) > self._maxsize:
                            self._lru.popitem(last=False)
                        self._hits += 1
                    return vec
            except Exception:
                pass
        self._misses += 1
        return None

    def put(self, text: str, vec: List[float]) -> None:
        key = self._key(text)
        with self._lock:
            self._lru[key] = vec
            if len(self._lru) > self._maxsize:
                self._lru.popitem(last=False)
        if self._redis:
            try:
                from shared.config import settings as _settings
                ttl = _settings.embed.cache_ttl
                self._redis.set(key, json.dumps(vec), ex=ttl)
            except Exception:
                pass

    def get_batch(self, texts: List[str]) -> Tuple[List[Optional[List[float]]], List[int]]:
        """Return cached embeddings and indices of cache misses."""
        results: List[Optional[List[float]]] = []
        miss_indices: List[int] = []
        for i, t in enumerate(texts):
            cached = self.get(t)
            results.append(cached)
            if cached is None:
                miss_indices.append(i)
        return results, miss_indices

    def put_batch(self, texts: List[str], vecs: List[List[float]]) -> None:
        for t, v in zip(texts, vecs):
            self.put(t, v)

    @property
    def stats(self) -> dict:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._lru)}


_cache = _EmbedCache()


def get_embed_cache() -> _EmbedCache:
    return _cache


# ── Embedding implementations ──────────────────────────────────


class HashEmbeddings(Embeddings):
    """Fallback embedding that deterministically hashes tokens into a dense vector."""

    def __init__(self, dim: int):
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def _bucket(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % self.dim

    def _vectorize(self, text: str) -> List[float]:
        buckets = [0.0] * self.dim
        for token in text.lower().split():
            idx = self._bucket(token)
            buckets[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in buckets)) or 1.0
        return [v / norm for v in buckets]

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._vectorize(t or "") for t in texts]


class OllamaEmbeddings(Embeddings):
    """Use Ollama /api/embed endpoint for embeddings — no torch needed."""

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed with LRU+Redis cache — only call Ollama for cache misses."""
        cached_results, miss_indices = _cache.get_batch(texts)

        if not miss_indices:
            logger.debug("Embedding cache: 100%% hit (%d texts)", len(texts))
            return cached_results  # type: ignore[return-value]

        # Call Ollama only for misses
        miss_texts = [texts[i] for i in miss_indices]
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            resp = client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": miss_texts},
            )
            resp.raise_for_status()
            new_vecs = resp.json()["embeddings"]

        # Cache new results and fill output
        _cache.put_batch(miss_texts, new_vecs)
        for idx, vec in zip(miss_indices, new_vecs):
            cached_results[idx] = vec

        logger.debug(
            "Embedding cache: %d/%d hits, %d computed",
            len(texts) - len(miss_indices), len(texts), len(miss_indices),
        )
        return cached_results  # type: ignore[return-value]


def _build_embeddings() -> Embeddings:
    provider = (settings.EMBED_PROVIDER or "ollama").lower()
    if provider == "hash":
        return HashEmbeddings(settings.EMBED_DIM)
    if provider == "ollama":
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("Using HashEmbeddings because tests are running")
            return HashEmbeddings(settings.EMBED_DIM)
        try:
            return OllamaEmbeddings(
                model=settings.ollama.model_embed,
                base_url=settings.ollama.base_url,
            )
        except Exception as exc:
            logger.warning("Falling back to HashEmbeddings: %s", exc)
            return HashEmbeddings(settings.EMBED_DIM)
    raise NotImplementedError(f"Unsupported EMBED_PROVIDER={provider}")


def get_embeddings() -> Embeddings:
    global _embeddings_singleton
    if _embeddings_singleton is None:
        with _embeddings_lock:
            if _embeddings_singleton is None:
                _embeddings_singleton = _build_embeddings()
    return _embeddings_singleton
