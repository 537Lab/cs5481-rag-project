# Evaluation format — SHARED STANDARD, QA SET, AND METRIC CODE

This directory holds the metric definitions the team agreed on **plus** the T4
delivery: `qa_set.csv`, `metrics.py`, and `judge_protocol.md`. It still contains
**no experiment results and no numbers** — result files go to `eval/results/`
(gitignored) and are written only by a command you actually ran.

| file | what it is | task |
| --- | --- | --- |
| `evidence.py` | gold spans, coverage, `is_retrieval_hit()` — strategy-independent | shared standard (frozen) |
| `qa_template.csv` | 2 SAMPLE rows showing the csv format only | shared standard |
| `qa_set.csv` | **35 items: 27 answerable + 8 unanswerable**, gold quotes verbatim in `data/raw/` | T4 |
| `metrics.py` | validate / retrieval / score / mock-demo, pure kernels + thin CLI | T4 |
| `judge_protocol.md` | how answer correctness is decided (human default, LLM rules) | T4 |
| `results/` | gitignored; every real run writes its json + provenance here | T2/T5 runs |

## What the assignment requires

- At least **20 question-answer pairs**.
- Compare **at least two chunking strategies** and report their impact on
  retrieval quality.
- Report **retrieval hit rate** and **answer correctness**.
- Answers must cite sources, and the system must abstain when there is no answer.

## Fix applied in v1.1: chunk ids must NOT be gold labels

`chunk_id` is an **output** of a chunking strategy. `fixed` vs `paragraph`, or
two different chunk sizes, produce different ids and different boundaries for
the same sentence. A gold label such as `expected_chunk_ids=rag_wikipedia#0003`
would therefore be invalid for one of the two strategies and would silently
make the comparison meaningless.

**Common standard = a verbatim quote from the ORIGINAL document.**

1. `qa_set.csv` stores `evidence_doc_id` + `evidence_quote` (exact substring of
   the source document text).
2. `eval/evidence.py::locate_evidence()` resolves that quote to a character
   span `[char_start, char_end)` in the original document. This span is the
   **same for every chunking strategy**.
3. A retrieved chunk is scored by `evidence_coverage()` — how much of that span
   it covers. Chunk ids are used only for display and citation, never for scoring.

`eval/qa_template.csv` contains **2 SAMPLE rows showing the format only**. They
are not evaluation data. The SAMPLE-001 quote was verified to exist verbatim at
chars 1651–1727 of `data/raw/rag_wikipedia.txt`.

`eval/qa_set.csv` (T4) follows the same 7 columns. Its `evidence_quote` values
are verbatim substrings of the four source documents; run
`python -m eval.metrics validate` to re-check all of them against the corpus.
Unanswerable items carry no gold evidence and declare `ABSENT_TOKENS: ...` in
`notes` — tokens that are asserted **not to occur anywhere** in `data/raw/`,
which the same command verifies. Coverage of the set: 10 items on
`rag_wikipedia`, 8 on `vector_db_wikipedia`, 5 on `word_embedding_wikipedia`, 4
on `bm25_wikipedia`; the 8 unanswerable items are 5 near-misses (topic-adjacent
but unsupported) and 3 out-of-domain.

## QA file format (`qa_template.csv`)

| column | meaning |
| --- | --- |
| `qid` | stable id, e.g. `Q001` |
| `question` | the question, exactly as asked |
| `reference_answer` | expected short answer (empty for `unanswerable`) |
| `evidence_doc_id` | `doc_id` of the ORIGINAL source document containing the answer |
| `evidence_quote` | verbatim substring of that document's text; located with `locate_evidence()` |
| `category` | `answerable` or `unanswerable` (empty evidence for the latter) |
| `notes` | why the item exists, ambiguity, grading caveats |

## Three DIFFERENT things — do not conflate them

| level | question | answered by | proves |
| --- | --- | --- | --- |
| 1. Citation ID valid | Was this id among this turn's retrieved chunks? | `citation_ids_valid()` | the id was not invented |
| 2. Quote exists | Is the quote verbatim text of that chunk? | `citation_quotes_verbatim()` | the pointer resolves to real source text |
| 3. Content supports the answer | Does that text actually support the claim? | **human or explicitly disclosed LLM judge**, in the evaluation task | factual support / answer correctness |

`verify_citation_structure()` combines **levels 1 + 2 only**. It is a structural
check. It **cannot** prove level 3, and it must never be reported as "answer
correctness" or "factual verification". `verify_citations()` is a backwards
compatible alias of that structural check.

## Metric definitions (agree before writing code)

- **Retrieval hit rate** = (# answerable questions where `is_retrieval_hit(top_k,
  span, min_coverage)` is True) / (total answerable questions). Report hit@1 and
  hit@3 separately and state `min_coverage` (suggested default 0.5). Same value
  for every strategy in a comparison.
- **Answer correctness** = (# questions whose `answer_text` is judged correct
  against `reference_answer`) / (total answerable questions). Default judge:
  **human grading**. LLM-as-judge is allowed only if disclosed, and any paid API
  call must be approved by the group first. Structural citation checks do NOT
  count as correctness.
- **Correct abstention rate** = (# `unanswerable` questions with
  `abstained == True`) / (total unanswerable questions). Also report the
  false-abstention rate on answerable questions.
- **Citation structure rate** = (# non-abstained answers passing
  `verify_citation_structure()`) / (total non-abstained answers). Structural
  only — see the three-level table above.

Report each metric **per chunking strategy**, using the same QA set, same top-k,
same `min_coverage`, same embedding model and same LLM. Otherwise the
comparison is meaningless.

### How the T4 code expresses these definitions

`eval/metrics.py` implements the four bullets above and nothing else. Every rate
is emitted as a `(numerator, denominator, rate)` triple — never a bare
percentage — so each number can be audited against the rows that produced it.

```command
python -m eval.metrics --help
python -m eval.metrics validate                      # gold quotes + ABSENT_TOKENS, offline
python -m eval.metrics retrieval --hits 1,3 --out eval/results/retrieval.json
python -m eval.metrics retrieval --chunking paragraph --out eval/results/retrieval_paragraph.json
python -m eval.metrics score --outputs eval/results/run.json
python -m eval.metrics score --outputs eval/results/run.json --grades eval/results/grades.csv
python -m eval.metrics mock-demo                     # MOCK plumbing, never a result
```

* `validate` needs no index and no key: it reads `data/raw/` and resolves every
  gold quote through `locate_evidence()`.
* `retrieval` needs the index built once (`python -m ragkit.cli ingest`) but **no
  API key** — the local ONNX embedder does the work. `--chunking` overrides
  `config.toml` for that run only, which is what the T2 fixed-vs-paragraph
  comparison reuses.
* `score` reads an answer run captured by T5 (format documented at the top of
  `metrics.py`) and recomputes abstention, citation structure, and hit@k of the
  context the run actually used. Chunk ids are round-tripped through
  `store.get_chunk()`, so a fabricated id is an error rather than a zero.
  `answer_correctness` stays the string `"pending human grading"` unless a
  `--grades` file is supplied: the code cannot report a correctness number it
  does not have.
* `min_coverage` defaults to `0.5`, is overridable, and is written into every
  report so hit rates from different settings are never silently compared.
* Every report embeds its own provenance: command line, UTC timestamp, chunking
  strategy/size/overlap, collection, embedding provider+dimension, LLM model,
  python version, and `label` (`REAL` or `MOCK`).

## Output location and honesty rules

Write results to `eval/results/` (gitignored). With every result file, record
the exact command, config, strategy, model and date. Never fabricate numbers,
never paste a MOCK output into a result, and never commit a result for a run
that did not happen.

## Intentionally NOT here

- Experiment results, comparison tables, or charts (T2/T5 runs; they land in
  `eval/results/`, which is gitignored).
- The answer run itself — producing `eval/results/run.json` is T5's job.
- Any chunk-size / overlap tuning, or paid LLM-as-judge calls (see
  `judge_protocol.md` §4 for the conditions under which those become allowed).
