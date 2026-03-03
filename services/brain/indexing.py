from __future__ import annotations
from typing import Any, Dict, List
import uuid

from .interfaces import Embeddings, VectorStore

# Fixed namespace for deterministic UUIDs
_UUID_NS = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _to_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_UUID_NS, str(chunk_id)))


class Indexer:
    def __init__(self, embed: Embeddings, vectorstore: VectorStore):
        self.embed = embed
        self.vectorstore = vectorstore

    def upsert_chunks(self, chunks: List[str], metas: List[Dict[str, Any]]) -> int:
        if len(chunks) != len(metas):
            raise ValueError("chunks and metas must have equal length")
        if not chunks:
            return 0

        vectors = self.embed.embed(chunks)
        if len(vectors) != len(chunks):
            raise RuntimeError("embeddings size mismatch")

        ids: List[str] = []
        payloads: List[Dict[str, Any]] = []
        for i, m in enumerate(metas):
            m = dict(m or {})
            orig_chunk_id = str(m.get("chunk_id", f"missing:{i}"))
            point_id = _to_point_id(orig_chunk_id)
            m["chunk_id"] = orig_chunk_id
            m["point_id"] = point_id
            ids.append(point_id)
            payloads.append(m)

        self.vectorstore.upsert(ids=ids, vectors=vectors, payloads=payloads)
        return len(chunks)
