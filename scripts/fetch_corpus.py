"""Fetch and freeze the openly licensed Kubernetes v1.35 corpus.

The four committed Wikipedia excerpts (``CORPUS_V0``) are immutable development
fixtures. This script verifies and preserves them, then downloads twelve official
Kubernetes documents from one pinned ``kubernetes/website`` commit. It writes the
combined manifest, provenance table, content hashes, and descriptive statistics.

Run from the repository root::

    python scripts/fetch_corpus.py

Stdlib only. No API key is required. Re-running against identical input preserves
the corpus id and generation timestamp, so a clean checkout remains reproducible.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"
FROZEN_PATH = RAW_DIR / "frozen_manifest.json"
SOURCES_PATH = RAW_DIR / "SOURCES.md"
CORPUS_DOC_PATH = ROOT / "docs" / "CORPUS.md"

K8S_REPOSITORY = "kubernetes/website"
K8S_TAG = "snapshot-initial-v1.35"
K8S_COMMIT = "8b8f5d5669f06aa7c1b4f0b7d371adc89c4c7564"
K8S_VERSION = "v1.35"
K8S_LICENSE = "CC BY 4.0"
K8S_LICENSE_URI = (
    "https://github.com/kubernetes/website/blob/"
    f"{K8S_COMMIT}/LICENSE"
)
USER_AGENT = "CS5481-RAG-corpus/1.0 (educational project)"

CORPUS_V0_IDS = (
    "rag_wikipedia",
    "vector_db_wikipedia",
    "word_embedding_wikipedia",
    "bm25_wikipedia",
)


@dataclass(frozen=True)
class CorpusPage:
    doc_id: str
    title: str
    source_path: str

    @property
    def output_path(self) -> str:
        return f"{self.doc_id}.md"

    @property
    def source_uri(self) -> str:
        return (
            f"https://github.com/{K8S_REPOSITORY}/blob/"
            f"{K8S_COMMIT}/{self.source_path}"
        )

    @property
    def download_uri(self) -> str:
        return (
            f"https://raw.githubusercontent.com/{K8S_REPOSITORY}/"
            f"{K8S_COMMIT}/{self.source_path}"
        )


PAGES = (
    CorpusPage(
        "k8s_v135_components",
        "Kubernetes Components",
        "content/en/docs/concepts/overview/components.md",
    ),
    CorpusPage(
        "k8s_v135_nodes",
        "Nodes",
        "content/en/docs/concepts/architecture/nodes.md",
    ),
    CorpusPage(
        "k8s_v135_pods",
        "Pods",
        "content/en/docs/concepts/workloads/pods/_index.md",
    ),
    CorpusPage(
        "k8s_v135_deployments",
        "Deployments",
        "content/en/docs/concepts/workloads/controllers/deployment.md",
    ),
    CorpusPage(
        "k8s_v135_services",
        "Services",
        "content/en/docs/concepts/services-networking/service.md",
    ),
    CorpusPage(
        "k8s_v135_configmaps",
        "ConfigMaps",
        "content/en/docs/concepts/configuration/configmap.md",
    ),
    CorpusPage(
        "k8s_v135_secrets",
        "Secrets",
        "content/en/docs/concepts/configuration/secret.md",
    ),
    CorpusPage(
        "k8s_v135_probes",
        "Configure Liveness, Readiness and Startup Probes",
        "content/en/docs/tasks/configure-pod-container/"
        "configure-liveness-readiness-startup-probes.md",
    ),
    CorpusPage(
        "k8s_v135_persistent_volumes",
        "Persistent Volumes",
        "content/en/docs/concepts/storage/persistent-volumes.md",
    ),
    CorpusPage(
        "k8s_v135_scheduling",
        "Assigning Pods to Nodes",
        "content/en/docs/concepts/scheduling-eviction/assign-pod-node.md",
    ),
    CorpusPage(
        "k8s_v135_kubectl_quick_reference",
        "kubectl Quick Reference",
        "content/en/docs/reference/kubectl/quick-reference.md",
    ),
    CorpusPage(
        "k8s_v135_stateless_deployment",
        "Run a Stateless Application Using a Deployment",
        "content/en/docs/tasks/run-application/run-stateless-application-deployment.md",
    ),
)

SHORTCODE_RE = re.compile(r"\{\{[<%]\s*(.*?)\s*[>%]\}\}", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_uri(source_path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{K8S_REPOSITORY}/"
        f"{K8S_COMMIT}/{source_path}"
    )


def fetch_source_text(source_path: str, cache: dict[str, str]) -> str:
    """Fetch one UTF-8 source file from the pinned commit, with per-run caching."""
    if source_path in cache:
        return cache[source_path]
    request = urllib.request.Request(
        _source_uri(source_path),
        headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw_bytes = response.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"source is not valid UTF-8: {source_path}") from exc
    cache[source_path] = text
    return text


def _safe_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe referenced source path: {value!r}")
    return path.as_posix()


def expand_external_content(raw_text: str, cache: dict[str, str]) -> str:
    """Inline Hugo includes and code samples from the same pinned commit."""

    def replace(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        include = re.fullmatch(r'include\s+"([^"]+)"', body)
        if include:
            name = _safe_relative_path(include.group(1))
            return "\n" + fetch_source_text(f"content/en/includes/{name}", cache) + "\n"

        if body.startswith("code_sample "):
            file_match = re.search(r'\bfile="([^"]+)"', body)
            if not file_match:
                raise ValueError(f"code_sample has no file attribute: {body}")
            name = _safe_relative_path(file_match.group(1))
            language_match = re.search(r'\blanguage="([^"]+)"', body)
            language = language_match.group(1) if language_match else Path(name).suffix[1:]
            sample = fetch_source_text(f"content/en/examples/{name}", cache).rstrip()
            return f"\n```{language}\n{sample}\n```\n"
        return match.group(0)

    return SHORTCODE_RE.sub(replace, raw_text)


def _strip_front_matter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ValueError("Markdown starts with unterminated YAML front matter")
    return text[closing + len("\n---\n") :]


def _front_matter_values(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ValueError("Markdown starts with unterminated YAML front matter")
    values = {}
    for line in text[4:closing].splitlines():
        if ":" not in line or line.startswith((" ", "\t", "-")):
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def _replace_shortcode(match: re.Match[str], metadata: dict[str, str]) -> str:
    """Keep meaningful labels while dropping Hugo presentation directives."""
    body = match.group(1).strip()
    if body.startswith("/"):
        return ""

    if body.startswith(("include ", "code_sample ")):
        raise ValueError(f"external shortcode was not expanded: {body}")

    text_value = re.search(r'\btext="([^"]+)"', body)
    if text_value:
        return text_value.group(1)

    feature_state = re.search(r'\bfeature_state="([^"]+)"', body)
    if feature_state:
        return feature_state.group(1)

    heading = re.fullmatch(r'heading\s+"([^"]+)"', body)
    if heading:
        return heading.group(1).replace("-", " ").title()

    if re.fullmatch(r'param\s+"version"', body):
        return K8S_VERSION

    if re.fullmatch(r"skew\s+currentVersion", body):
        return K8S_VERSION.removeprefix("v")

    if body.startswith("api-reference "):
        text_match = re.search(r'\btext="([^"]+)"', body)
        if text_match:
            return text_match.group(1)
        anchor_match = re.search(r'\banchor="([^"]+)"', body)
        if anchor_match:
            return anchor_match.group(1)
        page_match = re.search(r'\bpage="([^"]+)"', body)
        if page_match:
            resource = page_match.group(1).rsplit("/", 1)[-1]
            return resource.rsplit("-v", 1)[0].replace("-", " ").title()
        return "API reference"

    if body.startswith("figure "):
        caption = re.search(r'\bcaption="([^"]+)"', body)
        alt = re.search(r'\balt="([^"]+)"', body)
        label = caption or alt
        return f"[Figure: {label.group(1)}]" if label else ""

    if body == "version-check":
        minimum = metadata.get("min-kubernetes-server-version")
        if minimum:
            return (
                f"Your Kubernetes server must be version {minimum} or later. "
                "To check the version, use `kubectl version`."
            )
        return "To check the Kubernetes server version, use `kubectl version`."
    return ""


def clean_markdown(raw_text: str) -> str:
    """Remove site-only metadata without rewriting the document's prose."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    metadata = _front_matter_values(text)
    text = _strip_front_matter(text)
    text = HTML_COMMENT_RE.sub("", text)
    text = SHORTCODE_RE.sub(lambda match: _replace_shortcode(match, metadata), text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + "\n"


def fetch_page(page: CorpusPage, cache: dict[str, str]) -> tuple[str, int]:
    raw_text = fetch_source_text(page.source_path, cache)
    expanded_text = expand_external_content(raw_text, cache)
    cleaned = clean_markdown(expanded_text)
    if len(cleaned.strip()) < 800:
        raise ValueError(f"cleaned document is unexpectedly short: {page.doc_id}")
    return cleaned, len(expanded_text)


def load_corpus_v0() -> list[dict[str, Any]]:
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {str(entry["doc_id"]): entry for entry in entries}
    missing = [doc_id for doc_id in CORPUS_V0_IDS if doc_id not in by_id]
    if missing:
        raise ValueError(f"CORPUS_V0 manifest entries are missing: {missing}")

    preserved = []
    for doc_id in CORPUS_V0_IDS:
        entry = dict(by_id[doc_id])
        source = RAW_DIR / str(entry["path"])
        if not source.is_file():
            raise FileNotFoundError(f"CORPUS_V0 document is missing: {source}")
        entry["version"] = entry.get("version", "retrieved-2026-11-13")
        preserved.append(entry)
    return preserved


def build_manifest_entries(
    corpus_v0: list[dict[str, Any]], fetched: dict[str, tuple[str, int]]
) -> list[dict[str, Any]]:
    entries = list(corpus_v0)
    for page in PAGES:
        cleaned, raw_chars = fetched[page.doc_id]
        entries.append(
            {
                "doc_id": page.doc_id,
                "path": page.output_path,
                "title": page.title,
                "source_uri": page.source_uri,
                "license": K8S_LICENSE,
                "version": f"{K8S_TAG}@{K8S_COMMIT}",
                "notes": (
                    "Official Kubernetes Markdown; YAML front matter, HTML comments, "
                    "and Hugo presentation shortcodes removed deterministically. "
                    f"Source {raw_chars} chars; cleaned {len(cleaned)} chars."
                ),
            }
        )
    return entries


def build_document_records(
    entries: list[dict[str, Any]], raw_char_counts: dict[str, int]
) -> list[dict[str, Any]]:
    records = []
    seen_hashes: dict[str, str] = {}
    for entry in entries:
        path = RAW_DIR / str(entry["path"])
        data = path.read_bytes()
        digest = _sha256(data)
        if digest in seen_hashes:
            raise ValueError(
                f"duplicate content: {entry['doc_id']} and {seen_hashes[digest]}"
            )
        seen_hashes[digest] = str(entry["doc_id"])
        text = data.decode("utf-8")
        record = {
            "doc_id": entry["doc_id"],
            "path": entry["path"],
            "sha256": digest,
            "bytes": len(data),
            "chars": len(text),
            "version": entry["version"],
        }
        if entry["doc_id"] in raw_char_counts:
            record["source_chars"] = raw_char_counts[str(entry["doc_id"])]
        records.append(record)
    return records


def stable_generated_at(corpus_id: str) -> str:
    if FROZEN_PATH.is_file():
        previous = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
        if previous.get("corpus_id") == corpus_id and previous.get("generated_at"):
            return str(previous["generated_at"])
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def render_sources(entries: list[dict[str, Any]], records: list[dict[str, Any]]) -> str:
    record_by_id = {record["doc_id"]: record for record in records}
    lines = [
        "# Corpus provenance",
        "",
        "> Generated by `python scripts/fetch_corpus.py`. Do not edit generated rows by hand.",
        "",
        "## Formal corpus: Kubernetes v1.35",
        "",
        f"- Repository: `{K8S_REPOSITORY}`",
        f"- Tag: `{K8S_TAG}`",
        f"- Pinned commit: `{K8S_COMMIT}`",
        f"- Licence: [{K8S_LICENSE}]({K8S_LICENSE_URI})",
        "- Changes: inlined shared prerequisites and code samples from the same commit; removed "
        "YAML front matter, HTML comments, and presentation-only shortcode wrappers; kept prose, "
        "headings, tables, links, and code blocks.",
        "",
        "| doc_id | Title | Clean chars | Pinned source |",
        "| --- | --- | ---: | --- |",
    ]
    for entry in entries[len(CORPUS_V0_IDS) :]:
        chars = record_by_id[str(entry["doc_id"])]["chars"]
        lines.append(
            f"| `{entry['doc_id']}` | {entry['title']} | {chars} | "
            f"[source]({entry['source_uri']}) |"
        )

    lines.extend(
        [
            "",
            "## Preserved development corpus: CORPUS_V0",
            "",
            "These four CC BY-SA 4.0 Wikipedia excerpts remain byte-for-byte unchanged so "
            "existing development tests and QA drafts continue to work.",
            "",
            "| doc_id | Title | Licence | Source |",
            "| --- | --- | --- | --- |",
        ]
    )
    for entry in entries[: len(CORPUS_V0_IDS)]:
        lines.append(
            f"| `{entry['doc_id']}` | {entry['title']} | {entry['license']} | "
            f"[source]({entry['source_uri']}) |"
        )
    lines.extend(
        [
            "",
            "## Team rules",
            "",
            "1. Never put synthetic or MOCK documents in `data/raw/`.",
            "2. Do not change a frozen document, doc_id, version, or source URL in place.",
            "3. Re-run the fetch script and review all hash changes before creating a new "
            "snapshot.",
            "4. Keep attribution and licence metadata attached to every document.",
            "",
        ]
    )
    return "\n".join(lines)


def render_corpus_doc(
    corpus_id: str,
    generated_at: str,
    records: list[dict[str, Any]],
) -> str:
    formal = records[len(CORPUS_V0_IDS) :]
    lengths = [int(record["chars"]) for record in formal]
    source_total = sum(int(record["source_chars"]) for record in formal)
    cleaned_total = sum(lengths)
    removed_pct = (source_total - cleaned_total) / source_total * 100
    lines = [
        "# Formal corpus snapshot",
        "",
        f"- **corpus_id:** `{corpus_id}`",
        f"- **generated_at:** `{generated_at}`",
        f"- **formal domain documents:** {len(formal)} Kubernetes v1.35 pages",
        f"- **combined manifest:** {len(records)} documents "
        f"({len(formal)} formal + {len(CORPUS_V0_IDS)} preserved development documents)",
        f"- **source revision:** `{K8S_TAG}` / `{K8S_COMMIT}`",
        f"- **licence:** [{K8S_LICENSE}]({K8S_LICENSE_URI})",
        "",
        "## Why this corpus",
        "",
        "Kubernetes documentation has an explicit open licence, a fixed upstream revision, "
        "and a useful mixture of concept, task, and reference pages. The selected pages cover "
        "cluster components, workloads, networking, configuration, storage, scheduling, probes, "
        "and kubectl commands, which supports both answerable and abstention questions.",
        "",
        "## Descriptive statistics",
        "",
        f"- Clean characters: {cleaned_total:,} total",
        f"- Length: min {min(lengths):,}; median {statistics.median(lengths):,.0f}; "
        f"max {max(lengths):,}",
        f"- Deterministic cleaning removed {source_total - cleaned_total:,} of "
        f"{source_total:,} source characters ({removed_pct:.1f}%).",
        "",
        "| doc_id | chars | bytes | sha256 |",
        "| --- | ---: | ---: | --- |",
    ]
    for record in formal:
        lines.append(
            f"| `{record['doc_id']}` | {record['chars']} | {record['bytes']} | "
            f"`{str(record['sha256'])[:16]}…` |"
        )
    lines.extend(
        [
            "",
            "## Cleaning and downstream impact",
            "",
            "The script deterministically inlines shared prerequisites and YAML code samples from "
            "the same pinned commit, substitutes version placeholders, and removes site-only front "
            "matter, comments, and presentation wrappers. It retains the prose inside note/caution "
            "blocks, Markdown headings, code blocks, tables, and links. Long reference and task "
            "pages will produce more chunks than short concept pages; this is intentional "
            "variation for the T2 chunking comparison and T3 retrieval diagnostics.",
            "",
            "## Reproduce and verify",
            "",
            "```bash",
            "python scripts/fetch_corpus.py",
            "python -m pytest tests/test_loaders.py -q",
            "python -m ragkit.cli ingest",
            "```",
            "",
            "A second fetch against the same pinned commit must leave `git diff` empty. "
            "All formal experiments must cite the `corpus_id` above.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    corpus_v0 = load_corpus_v0()
    fetched: dict[str, tuple[str, int]] = {}
    source_cache: dict[str, str] = {}
    for page in PAGES:
        cleaned, raw_chars = fetch_page(page, source_cache)
        fetched[page.doc_id] = (cleaned, raw_chars)
        print(
            f"OK {page.doc_id:36s} source={raw_chars:6d} cleaned={len(cleaned):6d}"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        cleaned, _ = fetched[page.doc_id]
        (RAW_DIR / page.output_path).write_text(cleaned, encoding="utf-8")

    entries = build_manifest_entries(corpus_v0, fetched)
    manifest_text = json.dumps(entries, indent=2, ensure_ascii=False) + "\n"
    MANIFEST_PATH.write_text(manifest_text, encoding="utf-8")

    raw_char_counts = {
        doc_id: raw_chars for doc_id, (_, raw_chars) in fetched.items()
    }
    records = build_document_records(entries, raw_char_counts)
    snapshot_material = manifest_text.encode("utf-8") + "".join(
        f"{record['doc_id']}:{record['sha256']}\n" for record in records
    ).encode("utf-8")
    snapshot_hash = _sha256(snapshot_material)
    corpus_id = f"cs5481-k8s-v135-{len(records)}docs-{snapshot_hash[:12]}"
    generated_at = stable_generated_at(corpus_id)
    frozen = {
        "corpus_id": corpus_id,
        "generated_at": generated_at,
        "manifest_sha256": _sha256(manifest_text.encode("utf-8")),
        "source_repository": K8S_REPOSITORY,
        "source_tag": K8S_TAG,
        "source_commit": K8S_COMMIT,
        "documents": records,
    }
    FROZEN_PATH.write_text(
        json.dumps(frozen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    SOURCES_PATH.write_text(render_sources(entries, records), encoding="utf-8")
    CORPUS_DOC_PATH.write_text(
        render_corpus_doc(corpus_id, generated_at, records), encoding="utf-8"
    )

    print(f"\nFrozen {len(records)} documents as {corpus_id}")
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Wrote {FROZEN_PATH.relative_to(ROOT)}")
    print(f"Wrote {SOURCES_PATH.relative_to(ROOT)}")
    print(f"Wrote {CORPUS_DOC_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
