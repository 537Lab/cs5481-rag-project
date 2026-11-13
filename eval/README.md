# Evaluation format — DEFINITION + SHARED STANDARD ONLY (no experiment yet)

This directory defines the format and the metric definitions the team will use
later. It deliberately contains **no results, no scores, and no 20-item test
set**. Filling it in is a separate task (T4).

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

## Output location and honesty rules

Write results to `eval/results/` (gitignored). With every result file, record
the exact command, config, strategy, model and date. Never fabricate numbers,
never paste a MOCK output into a result, and never commit a result for a run
that did not happen.

## Intentionally NOT here yet

- The 20+ real QA pairs and their gold quotes (T4).
- The scoring script, comparison table, charts or any number (T4).
- The chunking comparison experiment itself (T2).
- Any chunk-size / overlap tuning, or paid LLM-as-judge calls.
