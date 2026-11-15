# Evaluation format and shared standard

This directory defines the QA format, the metric definitions and the result-submission
policy the team will use.

| file | what it is | status |
| --- | --- | --- |
| [`evidence.py`](evidence.py) | shared predicates: `locate_evidence`, `evidence_coverage`, `is_retrieval_hit` | frozen |
| [`qa_template.csv`](qa_template.csv) | 2 SAMPLE rows showing the I2 format | format example only |
| [`qa_set.csv`](qa_set.csv) | 35 QA pairs (27 answerable / 8 unanswerable), gold = verbatim quotes | **development set on `CORPUS_V0`**, to be re-validated against the frozen corpus |
| [`metrics.py`](metrics.py) | the team's single metric implementation, interface I3 | delivered, no formal numbers published yet |
| [`judge_protocol.md`](judge_protocol.md) | how answer correctness and unanswerable labels are decided by humans | protocol; grading not started |
| [`results/`](results/README.md) | `summary/` committed, `raw/` gitignored | `summary/` still empty |

The 20+ real QA pairs and the single metrics implementation therefore exist, but
no experiment result has been published here: the chunking comparison belongs to
T2, the answer artifacts (I4) to T5, and formal numbers need the frozen corpus
(I1). See "Output location and honesty rules" below.

The project's single source of truth for background, goals, the item-by-item mapping
of the instructor's requirements, the five tasks, the dependency/integration schedule
and the final deliverables is [`docs/PROJECT_PLAN.md`](../docs/PROJECT_PLAN.md).
This file only defines evaluation format and metric semantics.

## What the assignment requires

See [`docs/PROJECT_PLAN.md` §3](../docs/PROJECT_PLAN.md) for the verbatim requirements
and their current coverage. In short: at least **20 question-answer pairs**, a
comparison of **at least two chunking strategies** with its impact on retrieval
quality, **retrieval hit rate** and **answer correctness**, cited sources, and explicit
abstention when the knowledge base has no answer. Passing unit tests does not satisfy
any of these by itself.

## Gold labels are verbatim quotes, not chunk ids

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

## Metric definitions — ONE implementation, owned by T4

`eval/metrics.py` (T4) is the **only** implementation of these metrics. T2, T3 and
T5 must import it; nobody re-implements hit@k, correctness or abstention rates in
their own script. `eval/evidence.py` stays the shared predicate layer
(`locate_evidence`, `evidence_coverage`, `is_retrieval_hit`).

The public signatures are the frozen part of interface **I3**; the names below are
what other tasks must import:

```python
retrieval_hit_rate(items, spans, hits_by_qid, *, hit_levels, min_coverage)
answer_correctness(items, grades)
abstention_rates(items, outputs)
citation_structure_rate(items, outputs, *, chunk_of)
```

- **Retrieval hit rate** — `retrieval_hit_rate()` = (# answerable questions where
  `is_retrieval_hit(top_k, span, min_coverage)` is True) / (total answerable
  questions). Report hit@1 and hit@3 separately and state `min_coverage` (suggested
  default 0.5). Same value for every strategy in a comparison.
- **Answer correctness** — `answer_correctness()` = (# **answerable** questions
  judged correct against `reference_answer`) / (# answerable questions actually
  graded). Unanswerable questions are never in this denominator — a good refusal is
  an abstention result, not a correct answer — and `grading_coverage` is reported
  next to the rate so a partly graded set cannot read like a finished one. Default
  judge: **human grading**. LLM-as-judge is allowed only if disclosed, and any paid
  API call must be approved by the group first. Structural citation checks do NOT
  count as correctness.
- **Correct abstention rate** — `abstention_rates()` = (# `unanswerable` questions
  with `abstained == True`) / (total unanswerable questions). Also report the
  false-abstention rate on answerable questions. Labelling a question unanswerable
  is a human judgement attested per item as `REVIEWED_BY`; `ABSENT_TOKENS` alone is
  only a necessary condition ([`judge_protocol.md`](judge_protocol.md) §3).
- **Citation structure rate** — `citation_structure_rate()` = (# non-abstained
  answers passing `verify_citation_structure()`) / (total non-abstained answers).
  Structural only — see the three-level table above.

Report each metric **per chunking strategy**, using the same QA set, same top-k,
same `min_coverage`, same embedding model and same LLM. Otherwise the
comparison is meaningless.

## Running the T4 code

All commands run from the repository root and need no API key.

| command | what it proves |
| --- | --- |
| `python -m eval.metrics --help` | the I3 entry point is importable and callable |
| `python -m eval.metrics validate` | every gold quote is verbatim in `data/raw/`, labels are consistent, declared tokens really are absent |
| `python -m eval.metrics validate --require-reviewed` | fails until a named human attests each unanswerable item (`REVIEWED_BY`) |
| `python -m eval.metrics retrieval --hits 1,3 --out eval/results/raw/retrieval_fixed.json` | REAL hit@k over the built index (needs `python -m ragkit.cli ingest`) |
| `python -m eval.metrics retrieval --chunking paragraph --out ...` | the same QA against the other strategy's collection, without editing `config.toml` |
| `python -m eval.metrics score --run-id <run_id> --grades eval/results/raw/grades.csv` | scores T5's answer artifact `eval/answers/<run_id>.jsonl` |
| `python -m eval.metrics mock-demo` | metric maths and CLI wiring on MOCK fixtures; every number is labelled MOCK |

`score` reads interface I4: one JSON object per line, the nested `answer` object
plus `retrieved_chunk_ids`, `run_id` and `config_ref`. Flat records, `.json`
lists and `{'items': [...]}` envelopes from earlier drafts are still accepted, so
no existing caller has to change. A grading sheet written from that artifact is
refused if no grade cell is filled, so an ungraded run cannot look like a graded
one, and a run whose `answer.model` says it is a scripted double is called out
when `--label REAL` is used (`--label MOCK` is the honest flag for plumbing tests).
`--summary-dir DIR` together with `--formal`
writes the committed `config.json` / `metrics.json` / `run.md` bundle; it refuses
MOCK runs and refuses any run whose inputs are not frozen yet, which keeps
development numbers out of the directory the report reads.

## Frozen inputs and who consumes what

Formal numbers are only meaningful once the inputs are frozen. `CORPUS_V0`
(the 4 committed documents) is frozen for development only and is **not** the
formal experiment corpus unless the group explicitly falls back to it
(see [`docs/PROJECT_PLAN.md` §6.2](../docs/PROJECT_PLAN.md)). T4's `qa_set.csv`
gold quotes must be verbatim substrings of the frozen corpus snapshot, and every
strategy comparison must use the same frozen `qa_set.csv`.

The shared artifacts and their owners are defined in
[`docs/PROJECT_PLAN.md` §6.1](../docs/PROJECT_PLAN.md): I1 corpus snapshot (T1),
I2 `qa_set.csv` schema (T4), I3 `metrics.py` signatures (T4),
I4 `eval/answers/<run_id>.jsonl` answer artifacts (T5), I5 config/result schema
(T2 + T4). Freeze points and the T1 → T4 time-box are in
[`docs/PROJECT_PLAN.md` §6.6](../docs/PROJECT_PLAN.md).

## Output location and honesty rules

- **Do commit**: real, reproducible aggregate metrics, charts, config snapshots
  and a run manifest under [`results/summary/`](results/README.md).
- **Do not commit**: raw per-item outputs, logs and caches under
  `eval/results/raw/` (gitignored), MOCK outputs, AI-invented numbers, or any
  result for a run that did not happen.
- Every summary must record the exact command, config, strategy, model, date,
  executor and the T1/T4 frozen snapshot ids so a reviewer can recompute it.
  Full submission rules are in [`results/README.md`](results/README.md).
- Development runs on `CORPUS_V0` / MOCK fixtures must be labelled as such and
  must never be reported as formal experiment results.

Never fabricate numbers and never call `verify_citation_structure()` result
"answer correctness".

## Not here (yet)

- **Formal experiment numbers.** `results/summary/` is empty on purpose. The
  development hit rates are recorded in `RUNLOG.md` and in gitignored
  `results/raw/`, and `metrics.py` labels them `qa_set_status: development`.
- `eval/answers/<run_id>.jsonl` answer artifacts (T5). Until a real one exists,
  `score` has only been exercised against a MOCK artifact and answer correctness
  cannot be computed at all.
- Human answer grading, so `answer_correctness` stays "pending human grading".
- The frozen formal corpus (I1) and the QA re-validation that follows it: the 35
  current items were written against `CORPUS_V0` and stay the development set.
- The chunking comparison experiment itself (T2), any chunk-size / overlap
  tuning, and any paid LLM-as-judge call.

What each of these must produce, and by when, is in
[`docs/PROJECT_PLAN.md` §6.5](../docs/PROJECT_PLAN.md).
