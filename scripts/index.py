#!/usr/bin/env python3
"""LVCA RAG Indexer — index documents from knowledge/ into Qdrant."""
from __future__ import annotations

import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.brain.chunking import split_with_metadata
from services.brain.embeddings import get_embeddings
from services.brain.vectorstore import get_vectorstore
from services.brain.indexing import Indexer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("indexer")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
SUPPORTED_EXT = {".md", ".txt", ".pdf"}


def read_file(path: Path) -> str:
    """Read a file and return its text content."""
    if path.suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("pypdf not installed, skipping %s. Install: pip install pypdf", path.name)
            return ""
        except Exception as e:
            logger.error("Failed to read PDF %s: %s", path.name, e)
            return ""
    else:
        return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    if not KNOWLEDGE_DIR.exists():
        print(f"Knowledge directory not found: {KNOWLEDGE_DIR}")
        print("Create it and add .md, .txt, or .pdf files.")
        return 1

    # Collect files
    files = sorted(
        f for f in KNOWLEDGE_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXT
    )

    if not files:
        print(f"No documents found in {KNOWLEDGE_DIR}")
        print(f"Supported formats: {', '.join(SUPPORTED_EXT)}")
        return 1

    print(f"Found {len(files)} document(s) in {KNOWLEDGE_DIR}")

    # Initialize RAG components
    print("Initializing embeddings...")
    embed = get_embeddings()
    print("Initializing vector store...")
    vs = get_vectorstore()
    indexer = Indexer(embed=embed, vectorstore=vs)

    total_chunks = 0
    for i, fpath in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {fpath.name}")

        text = read_file(fpath)
        if not text.strip():
            print(f"  Skipping (empty)")
            continue

        # Chunk the document
        chunks_meta = split_with_metadata(
            text=text,
            filename=fpath.name,
            document_id=i,
            chunk_size=800,
            overlap=120,
        )

        if not chunks_meta:
            print(f"  No chunks generated")
            continue

        # Prepare for indexing
        texts = [c["text"] for c in chunks_meta]
        metas = []
        for j, c in enumerate(chunks_meta):
            c["chunk_id"] = f"{fpath.stem}:{j}"
            metas.append(c)

        # Index
        n = indexer.upsert_chunks(texts, metas)
        total_chunks += n
        print(f"  Indexed {n} chunks")

    print(f"\nDone! Total: {total_chunks} chunks indexed from {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
