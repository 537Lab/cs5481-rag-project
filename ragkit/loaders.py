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

import hashlib
import json
from pathlib import Path
from typing import Any

from ragkit.contracts import Document

REQUIRED_FIELDS = ("doc_id", "path", "title", "source_uri", "license")
NON_EMPTY_FIELDS = ("doc_id", "path", "title", "license")


def _read_utf8(path: Path, *, kind: str) -> str:
    """Read text with an explicit, human-readable UTF-8 validation error."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{kind} is not valid UTF-8: {path}") from exc


def load_manifest(manifest_path: str | Path) -> list[dict[str, Any]]:
    """Read and validate the manifest. Fail early with a readable error."""
    path = Path(manifest_path)
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")
    data = json.loads(_read_utf8(path, kind="manifest"))
    if not isinstance(data, list):
        raise ValueError(f"manifest must be a JSON list of objects: {path}")

    seen_doc_ids: set[str] = set()
    seen_paths: dict[Path, str] = {}
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"manifest entry #{i} must be an object")
        missing = [key for key in REQUIRED_FIELDS if key not in entry]
        if missing:
            raise ValueError(f"manifest entry #{i} is missing {missing}")
        empty = [
            key
            for key in NON_EMPTY_FIELDS
            if not isinstance(entry[key], str) or not entry[key].strip()
        ]
        if empty:
            raise ValueError(f"manifest entry #{i} has empty fields {empty}")

        source_uri = entry["source_uri"]
        if not isinstance(source_uri, str):
            raise ValueError(f"manifest entry #{i} has a non-string source_uri")
        if not source_uri.strip() and not str(entry["license"]).startswith("MOCK"):
            raise ValueError(f"manifest entry #{i} has an empty source_uri")

        doc_id = str(entry["doc_id"])
        if doc_id in seen_doc_ids:
            raise ValueError(f"duplicate doc_id in manifest: {doc_id}")
        seen_doc_ids.add(doc_id)

        source = Path(str(entry["path"]))
        if not source.is_absolute():
            source = path.parent / source
        canonical_source = source.resolve()
        if canonical_source in seen_paths:
            raise ValueError(
                "duplicate document path in manifest: "
                f"doc_id={doc_id!r} and doc_id={seen_paths[canonical_source]!r} "
                f"both reference {source}"
            )
        seen_paths[canonical_source] = doc_id
    return data


def load_documents(manifest_path: str | Path) -> list[Document]:
    """Load every manifest entry into a Document, preserving provenance."""
    manifest_path = Path(manifest_path)
    documents: list[Document] = []
    seen_content: dict[str, str] = {}
    for entry in load_manifest(manifest_path):
        source = Path(str(entry["path"]))
        if not source.is_absolute():
            source = manifest_path.parent / source
        if not source.is_file():
            raise FileNotFoundError(
                f"document for doc_id={entry['doc_id']!r} not found: {source}"
            )
        text = _read_utf8(source, kind=f"document for doc_id={entry['doc_id']!r}")
        if not text.strip():
            raise ValueError(f"document is empty: {source}")

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if content_hash in seen_content:
            raise ValueError(
                "duplicate document content: "
                f"doc_id={entry['doc_id']!r} duplicates doc_id={seen_content[content_hash]!r}"
            )
        seen_content[content_hash] = str(entry["doc_id"])

        documents.append(
            Document(
                doc_id=str(entry["doc_id"]),
                title=str(entry["title"]),
                text=text,
                source_uri=str(entry["source_uri"]),
                license=str(entry["license"]),
                meta={k: v for k, v in entry.items() if k not in REQUIRED_FIELDS},
            )
        )
    return documents
