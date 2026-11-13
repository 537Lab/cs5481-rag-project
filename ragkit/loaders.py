"""M1 - Document ingestion.

INPUT   data/raw/manifest.json + the files it points at (UTF-8 .txt / .md)
OUTPUT  list[Document]
DEPENDS stdlib only
DOES NOT chunk, embed, or touch the vector database.

The manifest is the single source of truth for provenance. Each real document
must declare `doc_id`, `path`, `title`, `source_uri` and `license` so that a
citation can always be traced back to where the text came from.

manifest.json format:
[
  {
    "doc_id": "rag_wikipedia",
    "path": "rag_wikipedia.txt",
    "title": "Retrieval-augmented generation",
    "source_uri": "https://en.wikipedia.org/wiki/...",
    "license": "CC BY-SA 4.0",
    "notes": "optional"
  }
]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragkit.contracts import Document

REQUIRED_FIELDS = ("doc_id", "path", "title")


def load_manifest(manifest_path: str | Path) -> list[dict[str, Any]]:
    """Read and validate the manifest. Fail early with a readable error."""
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"manifest must be a JSON list of objects: {path}")

    seen: set[str] = set()
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"manifest entry #{i} must be an object")
        missing = [key for key in REQUIRED_FIELDS if not entry.get(key)]
        if missing:
            raise ValueError(f"manifest entry #{i} is missing {missing}")
        doc_id = str(entry["doc_id"])
        if doc_id in seen:
            raise ValueError(f"duplicate doc_id in manifest: {doc_id}")
        seen.add(doc_id)
    return data


def load_documents(manifest_path: str | Path) -> list[Document]:
    """Load every manifest entry into a Document, preserving provenance."""
    manifest_path = Path(manifest_path)
    documents: list[Document] = []
    for entry in load_manifest(manifest_path):
        source = Path(str(entry["path"]))
        if not source.is_absolute():
            source = manifest_path.parent / source
        if not source.is_file():
            raise FileNotFoundError(
                f"document for doc_id={entry['doc_id']!r} not found: {source}"
            )
        text = source.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"document is empty: {source}")
        documents.append(
            Document(
                doc_id=str(entry["doc_id"]),
                title=str(entry["title"]),
                text=text,
                source_uri=str(entry.get("source_uri", "")),
                license=str(entry.get("license", "")),
                meta={k: v for k, v in entry.items() if k not in REQUIRED_FIELDS},
            )
        )
    return documents
