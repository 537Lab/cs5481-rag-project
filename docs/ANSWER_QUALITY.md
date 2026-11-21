# T5 Answer Quality

## T5 Overview
T5 extends generation and CLI functionality on main commit 848d7c6. No paid API was called.

## Answer Generation Workflow
Retrieved chunks enter the existing grounded prompt. The model returns text with inline chunk IDs. Empty context, model refusal, invalid output types, invented IDs, missing citations and uncovered sentences lead to abstention. API transport errors propagate so operators can distinguish infrastructure failures.

## Citation Validation
Citation IDs must belong to this retrieval turn and document IDs must match. Existing interfaces are preserved.

## Quote Verification
Citation excerpts are copied from the first 200 characters of retrieved chunks. Verification requires a nonempty verbatim substring. This excerpt may omit the evidence supporting a particular claim.

## Claim-level Citation Coverage
A conservative sentence/list heuristic checks for a citation in each text unit. This can reject headings and cannot detect unsupported clauses within one sentence. Citation punctuation is normalized before checking. Semantic support remains subject to human grading.

## Refusal Handling
The original Answer schema remains frozen. Refusals preserve raw model text where available. The CLI displays the deterministic refusal reason from the same gates used by generation. Invalid non-string output is represented by an empty raw string under the frozen contract, so it shares the invalid_or_empty_output reason. Empty questions raise a validation error. Transport failures are errors rather than claims about evidence quality.

## JSONL Output Schema
`python -m ragkit.cli batch --questions eval/qa_set.csv --run-id RUN --output eval/answers/RUN.jsonl`

This REAL command requires an approved API configuration. Each line contains qid, nested answer (question, answer_text, abstained, citations, model, raw), retrieved_chunk_ids, run_id and config_ref. All input rows are validated before generation. Existing output paths are refused. Results are accumulated before opening the output. T4 load_outputs compatibility is tested using MOCK answers. config_ref points to the selected TOML, not an immutable experiment snapshot. Formal provenance integration remains Pending.

## Demo Instructions
From the repository root run `python -m demo.run` or `python -m ragkit.cli offline-demo`. Both use synthetic fixtures, require no key and display MOCK / OFFLINE. The output shows a valid answer, its source excerpt, an invented-ID refusal and an insufficient-evidence refusal. The scripted normal answer now selects a retrieved chunk containing 8080.

## Testing and Validation
On 2026-11-20, tests/test_generation.py passed 19 tests, including invalid outputs, multiple claims and I4 export accepted by T4 load_outputs. Ruff passed. The CLI offline-demo and demo.run executed successfully. Full pytest encountered a Windows native access violation in Chroma upsert in tests/test_store.py. A pyreadline cleanup warning also appeared after generation tests. No full-suite success is claimed.

## Limitations and Failure Cases
Valid citations and verbatim excerpts do not establish factual support. The original regression test deliberately allows a structurally valid answer that contradicts its evidence. Coverage is heuristic. Provider exceptions are propagated. Batch output is buffered in memory, flushed to a temporary file and published atomically without overwriting an existing destination. Temporary files are cleaned when publication fails. Filesystem metadata durability across power loss is not guaranteed. MOCK retrieval is synthetic and provides no retrieval-quality evidence.

## Pending Integration Work
GitHub browser identity ziqilin669 was verified and Issue #5 was self-assigned while remaining Open. Its live requirements were read. CLI authentication is separate from browser authentication. Obtain approved LLM configuration (C3), integrated frozen T1 corpus and T3 index, and frozen T4 QA (I2). Produce real I4 answers and have T4 perform independent grading. Review PR #15 separately, without merging its unmerged QA into this branch. Human review signatures remain Pending. Shared CLI changes require team review under CONTRIBUTING.

## Additional validation on 2026-11-20
The batch command now supports explicit `--mock` with a mandatory MOCK- run ID. Run `python -m ragkit.cli batch --mock --questions demo/questions.csv --run-id MOCK-example --output eval/results/raw/MOCK-example.jsonl`. The scripted synthetic pipeline is in demo/mock_pipeline.py. Two records were exported successfully to the ignored raw directory in an actual CLI run. Temporary-file writing followed by a no-overwrite atomic publication prevents partial output files and preserves concurrent-run safety. On Windows publication uses rename, which fails if the destination exists. On other platforms it uses a hard link. The earlier statement about nontransactional batch writes is superseded by this change.

After additional malformed-input and provider-error tests, the generation and offline pipeline selection passed 29 tests. Ruff passed. The full-suite Chroma failure remains unresolved. Real LLM integration, formal immutable config snapshots remain Pending.

## Latest independent validation
Generation and offline pipeline tests passed 37 tests on 2026-11-20. This includes a subprocess MOCK batch command, per-gate diagnostics and publication-failure cleanup. Ruff passed. No real LLM was called.

Final regression on 2026-11-20: `python -m pytest --ignore=tests/test_store.py -o addopts="" -q` reported 156 passed and 3 skipped. Full pytest was retried outside the sandbox and still crashed in Chroma Rust upsert (tests/test_store.py), establishing that moving outside the sandbox did not resolve it. `python -m demo.run`, `ruff check .` and `git diff --check` passed. A pyreadline destructor warning remained after pytest. No T3 files were modified.
