# Corpus provenance (READ THIS BEFORE ADDING DOCUMENTS)

The files in `data/raw/` are **real, publicly licensed documents**, not synthetic
data. They are short **excerpts** of English Wikipedia articles, retrieved as
plain text via the MediaWiki API (`action=query&prop=extracts&explaintext=1`).
`scripts/fetch_corpus.py` reproduces the download exactly.

| doc_id | Article | Source URL | Excerpt |
| --- | --- | --- | --- |
| `rag_wikipedia` | Retrieval-augmented generation | <https://en.wikipedia.org/wiki/Retrieval-augmented_generation> | lead + early technical sections |
| `vector_db_wikipedia` | Vector database | <https://en.wikipedia.org/wiki/Vector_database> | lead + early technical sections |
| `word_embedding_wikipedia` | Word embedding | <https://en.wikipedia.org/wiki/Word_embedding> | lead + early technical sections |
| `bm25_wikipedia` | Okapi BM25 | <https://en.wikipedia.org/wiki/Okapi_BM25> | lead + early technical sections |

- **Retrieved:** 2026-11-13, for CS5481 Topic 5 (educational use).
- **Attribution:** Wikipedia contributors.
- **Licence:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
  The text in `data/raw/*.txt` is provided under that licence. Changes made:
  shortened to a plain-text excerpt; wiki markup and reference lists removed.
  The Python code in this repository is not part of that derived text.
- `data/raw/manifest.json` carries `source_uri` and `license` per document, so
  M1 can pass provenance to M4/M5 and every citation can be traced back here.

## Rules for the team

1. **Never** put synthetic / mock documents in `data/raw/`. Mock documents live
   in `tests/fixtures/` and are labelled `MOCK` on their first line.
2. When adding a real document, add its `doc_id`, `path`, `title`, `source_uri`
   and `license` to `manifest.json` **and** a row to this table.
3. Do not add documents whose licence forbids redistribution.
4. Keep excerpts short: this is a starter corpus for plumbing, not the final
   experiment dataset. The team will expand it in a later PR.
