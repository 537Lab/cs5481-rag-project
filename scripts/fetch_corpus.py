"""OPTIONAL one-off helper: (re)fetch the openly licensed starter corpus.

This is NOT needed to run the project - data/raw/*.txt is committed, so
`cli ingest` works offline. Run it only when the team wants to refresh or
extend the corpus:

    # direct connection
    python scripts/fetch_corpus.py

    # behind a proxy (Clash / 肥猫云 / any HTTP proxy)
    HTTPS_PROXY=http://127.0.0.1:7897 python scripts/fetch_corpus.py

Source: Wikipedia MediaWiki API `prop=extracts&explaintext=1` (plain text).
Each file is a short EXCERPT of the lead + early technical sections. See
data/raw/SOURCES.md for attribution, licence and exact URLs.

Stdlib only. No API key required.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
API = "https://en.wikipedia.org/w/api.php"
LICENSE = "CC BY-SA 4.0"
USER_AGENT = "CS5481-RAG-baseline/1.0 (educational project; contact: course group)"

# (doc_id, Wikipedia page title, max characters of the excerpt)
PAGES = [
    ("rag_wikipedia", "Retrieval-augmented generation", 4200),
    ("vector_db_wikipedia", "Vector database", 3600),
    ("word_embedding_wikipedia", "Word embedding", 3600),
    ("bm25_wikipedia", "Okapi BM25", 3200),
]


def fetch_plaintext(title: str) -> str:
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "format": "json",
            "formatversion": 2,
            "redirects": 1,
            "titles": title,
        }
    )
    request = urllib.request.Request(
        f"{API}?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    pages = payload["query"]["pages"]
    if not pages or "extract" not in pages[0]:
        raise RuntimeError(f"Wikipedia returned no plaintext extract for {title!r}")
    return pages[0]["extract"]


def excerpt(text: str, limit: int) -> str:
    """Cut at a paragraph or sentence boundary, never mid-word."""
    text = text.strip()
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = max(head.rfind("\n\n"), head.rfind(". "))
    if cut < limit // 2:
        cut = limit
    return head[:cut].strip()


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for doc_id, title, limit in PAGES:
        text = fetch_plaintext(title)
        body = excerpt(text, limit)
        if len(body) < 200:
            raise RuntimeError(f"excerpt too short for {title!r}; check the API response")
        (RAW_DIR / f"{doc_id}.txt").write_text(body + "\n", encoding="utf-8")
        manifest.append(
            {
                "doc_id": doc_id,
                "path": f"{doc_id}.txt",
                "title": title,
                "source_uri": "https://en.wikipedia.org/wiki/"
                + urllib.parse.quote(title.replace(" ", "_")),
                "license": LICENSE,
                "notes": f"Plain-text excerpt ({len(body)} chars) of the Wikipedia article, "
                "fetched via the MediaWiki API. Attribution in SOURCES.md.",
            }
        )
        print(f"OK {doc_id:28s} {len(body):6d} chars  <- {title}")

    (RAW_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {len(manifest)} documents and data/raw/manifest.json")
    print("Remember: data/raw/SOURCES.md carries the CC BY-SA attribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
