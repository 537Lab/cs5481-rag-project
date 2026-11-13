"""M1 tests. Real corpus is committed, so these run offline in CI."""

from __future__ import annotations

import json

import pytest

from ragkit.config import ROOT
from ragkit.loaders import load_documents, load_manifest

REAL_MANIFEST = ROOT / "data" / "raw" / "manifest.json"
MOCK_MANIFEST = ROOT / "tests" / "fixtures" / "manifest.json"


def test_real_manifest_declares_provenance():
    entries = load_manifest(REAL_MANIFEST)
    assert len(entries) >= 3
    for entry in entries:
        assert entry["source_uri"].startswith("https://"), entry
        assert entry["license"], entry


def test_load_real_documents():
    documents = load_documents(REAL_MANIFEST)
    assert len(documents) >= 3
    assert all(len(doc.text) > 500 for doc in documents)
    assert all(doc.source_uri and doc.license for doc in documents)
    assert len({doc.doc_id for doc in documents}) == len(documents)


def test_load_mock_fixtures_are_labelled():
    documents = load_documents(MOCK_MANIFEST)
    assert len(documents) == 2
    assert all(doc.text.startswith("MOCK FIXTURE") for doc in documents)
    assert all(doc.license.startswith("MOCK") for doc in documents)


def test_manifest_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nope.json")


def test_manifest_duplicate_doc_id_raises(tmp_path):
    path = tmp_path / "manifest.json"
    entry = {"doc_id": "dup", "path": "a.txt", "title": "A"}
    path.write_text(json.dumps([entry, entry]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate doc_id"):
        load_documents(path)


def test_manifest_entry_missing_field_raises(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps([{"doc_id": "x"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        load_documents(path)


def test_referenced_document_missing_raises(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps([{"doc_id": "x", "path": "absent.txt", "title": "X"}]), encoding="utf-8"
    )
    with pytest.raises(FileNotFoundError, match="absent.txt"):
        load_documents(path)


def test_empty_document_rejected(tmp_path):
    (tmp_path / "empty.txt").write_text("   \n", encoding="utf-8")
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps([{"doc_id": "x", "path": "empty.txt", "title": "X"}]), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="empty"):
        load_documents(path)
