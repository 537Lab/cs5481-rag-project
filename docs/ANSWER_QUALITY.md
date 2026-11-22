# T5 Answer Quality

## Integrated handoff validation (2026-11-22)

`python -m demo.validate_export` now verifies the known synthetic question IDs,
normal-answer/refusal states, citation membership in retrieved IDs, sidecar
references and QA/manifest hashes after T4 loading. Tampered refusal state,
configuration reference and QA hash are covered by negative regression tests.
The offline command passed; generation, offline pipeline and T4 metric tests
reported 130 passed in the agent's local environment. `git diff --check` passed.
Ruff is unavailable in that environment; no new local lint success is claimed.
This checks the scripted handoff and does not grade real answers or report metrics.

## Qualitative failure examples for the demo

These are synthetic illustrations of the existing rules, not measured failure
frequencies or human grading records. See `demo/README.md` for the presentation.

| Case | Generator behavior | Interpretation |
| --- | --- | --- |
| Answer cites a chunk absent from this retrieval turn | Abstains with `unknown_citation_id` | Prevents invented IDs, but cannot recover missing evidence. |
| One sentence has a valid citation; the next has none | Abstains with `uncovered_claim` | Conservative coverage can also reject an uncited heading or harmless formatting. |
| Source says port 8080; answer says port 9090 with that source's real ID | May pass structural checks | Verbatim excerpts and valid IDs cannot detect contradiction. T4 must grade support independently. |
| Model returns `NO_ANSWER` although retrieved evidence contains the answer | Abstains with `model_reported_insufficient_evidence` | Potential over-refusal; appropriateness requires the frozen QA and evidence, not this reason code alone. |
| Supporting text occurs after the first 200 characters of a chunk | Full cited chunk is now exported | Older prefix-only artifacts can omit evidence. New exports retain the full source span; semantic support still requires grading. |

No failure rate or answer correctness is inferred from these examples.

## T5 Overview
T5 extends generation and CLI functionality on main commit 848d7c6. No paid API was called.

## Answer Generation Workflow
Retrieved chunks enter the existing grounded prompt. The model returns text with inline chunk IDs. Empty context, model refusal, invalid output types, invented IDs, missing citations and uncovered sentences lead to abstention. API transport errors propagate so operators can distinguish infrastructure failures.

## Citation Validation
Citation IDs must belong to this retrieval turn and document IDs must match. Existing interfaces are preserved.

## Quote Verification
Citation quotes now preserve the complete retrieved chunk text, including boundary whitespace, instead of taking the first 200 characters. This prevents an export cutoff from dropping a supporting sentence later in the cited chunk. The quote is source text, not a model-generated or gold-selected span. Verification still checks only a nonempty verbatim substring; a full chunk can be irrelevant or contradict the answer. The CLI's short quote preview is separate from the full quote stored in Answer and JSONL.

## Claim-level Citation Coverage
A conservative sentence/list heuristic checks for a citation in each text unit. This can reject headings and cannot detect unsupported clauses within one sentence. Citation punctuation is normalized before checking. Semantic support remains subject to human grading.

## Refusal Handling
The original Answer schema remains frozen. Refusals preserve raw model text where available. The CLI displays the deterministic refusal reason from the same gates used by generation. Invalid non-string output is represented by an empty raw string under the frozen contract, so it shares the invalid_or_empty_output reason. Empty questions raise a validation error. Transport failures are errors rather than claims about evidence quality.

## JSONL Output Schema
`python -m ragkit.cli batch --questions eval/qa_set.csv --run-id RUN --output eval/answers/RUN.jsonl`

This REAL command requires an approved API configuration. Each line contains qid, nested answer (question, answer_text, abstained, citations, model, raw), retrieved_chunk_ids, run_id and config_ref. All input rows are validated before generation. Existing output paths are refused. Results are accumulated before opening the output. T4 load_outputs compatibility is tested using MOCK answers. config_ref points to the per-run JSON sidecar, including effective settings and input hashes; it does not certify formal experiment approval.

## Demo Instructions
From the repository root run `python -m demo.run` or `python -m ragkit.cli offline-demo`. Both use synthetic fixtures, require no key and display MOCK / OFFLINE. The output shows a valid answer, its source excerpt, an invented-ID refusal and an insufficient-evidence refusal. The scripted normal answer now selects a retrieved chunk containing 8080.

## Testing and Validation
On 2026-11-20, tests/test_generation.py passed 19 tests, including invalid outputs, multiple claims and I4 export accepted by T4 load_outputs. Ruff passed. The CLI offline-demo and demo.run executed successfully. Full pytest encountered a Windows native access violation in Chroma upsert in tests/test_store.py. A pyreadline cleanup warning also appeared after generation tests. No full-suite success is claimed.

## Limitations and Failure Cases
Valid citations and verbatim excerpts do not establish factual support. The original regression test deliberately allows a structurally valid answer that contradicts its evidence. Coverage is heuristic. Provider exceptions are propagated. Batch output is buffered in memory, flushed to a temporary file and published atomically without overwriting an existing destination. Temporary files are cleaned when publication fails. Filesystem metadata durability across power loss is not guaranteed. MOCK retrieval is synthetic and provides no retrieval-quality evidence.

## Current integration and remaining work
As checked on 2026-11-22, main includes T3 #11 and T4 #15. This delivery branch consolidates T5 #22, #24 and #25 into #26: local Ollama configuration, full citation export, handoff integrity checks, diagnostics and a live demo. The user reported team agreement to local `qwen3:4b-instruct`; the earlier C3-pending notes below are historical. A 36-answer baseline and separately identified citation-fix smoke outputs exist locally. Preserve the baseline and its grading inputs. Independent human grading and adjudication remain T4 responsibilities and are not attested by this code work. Non-author review and merge remain required; Issue #5 stays Open. No answer-correctness or abstention metric is claimed by T5.

## Additional validation on 2026-11-20
The batch command now supports explicit `--mock` with a mandatory MOCK- run ID. Run `python -m ragkit.cli batch --mock --questions demo/questions.csv --run-id MOCK-example --output eval/results/raw/MOCK-example.jsonl`. The scripted synthetic pipeline is in demo/mock_pipeline.py. Two records were exported successfully to the ignored raw directory in an actual CLI run. Temporary-file writing followed by a no-overwrite atomic publication prevents partial output files and preserves concurrent-run safety. On Windows publication uses rename, which fails if the destination exists. On other platforms it uses a hard link. The earlier statement about nontransactional batch writes is superseded by this change.

After additional malformed-input and provider-error tests, the generation and offline pipeline selection passed 29 tests. Ruff passed. The full-suite Chroma failure remains unresolved. Real LLM integration, formal immutable config snapshots remain Pending.

## Latest independent validation
Generation and offline pipeline tests passed 37 tests on 2026-11-20. This includes a subprocess MOCK batch command, per-gate diagnostics and publication-failure cleanup. Ruff passed. No real LLM was called.

Final regression on 2026-11-20: `python -m pytest --ignore=tests/test_store.py -o addopts="" -q` reported 156 passed and 3 skipped. Full pytest was retried outside the sandbox and still crashed in Chroma Rust upsert (tests/test_store.py), establishing that moving outside the sandbox did not resolve it. `python -m demo.run`, `ruff check .` and `git diff --check` passed. A pyreadline destructor warning remained after pytest. No T3 files were modified.

## T5 configuration provenance follow-up (2026-11-21)
Batch exports now create an exclusive `<output-stem>.config.json` sidecar. Every I4 row points config_ref at this file. It records run ID, MOCK/REAL mode, chunking, top_k, score floor, embedding provider/model, LLM settings, QA file hash and manifest hash. MOCK configuration reflects the synthetic pipeline. Existing snapshots are protected and snapshots created by this invocation are removed if publication fails. QA and manifest hashes identify input bytes, but do not attest human review or corpus freezing. Source document content hashes and immutable index/model versions still require the team's formal experiment bundle. min_coverage belongs to T4 evaluation and is not a generation setting. No credentials or environment variables are serialized.

Follow-up validation: 38 generation/offline pipeline tests passed and Ruff passed. Real LLM calls remain unexecuted. Earlier statements saying config_ref points to the mutable TOML are superseded by this change.

## Additional output and CSV guards (2026-11-21)
Citation-only output now refuses with missing_answer_text. Chinese sentence boundaries are checked even without spaces, and trailing citations after Chinese punctuation are attached to their preceding sentence. This remains a structural heuristic, not semantic grading. Batch CSV input now rejects missing required headers, duplicate header names and extra row values before model construction.

Validation: 44 generation/offline pipeline tests passed; Ruff passed. Existing Windows pyreadline cleanup warning persists. No paid API calls were made.

## Reproducible generator diagnostics and live demo (2026-11-22)

`demo.inspect_answers` reads existing I4 records through T4's loader and reuses
T5's gate and citation-structure helpers against the matching stored chunks.
It requires no gold, embedding query or model call, and produces no metrics or
grades. Missing chunks are explicitly reported as an incomplete index rather
than being misinterpreted as model refusal. See `demo/T5_HANDOFF.md` for usage.

Inspection of the original local-model batch reproduced K06's two uncited
sentences (`uncovered_claim`) and K24's uncited command (`missing_citations`).
Those gates are enforcing the agreed citation policy. The other model-level
`NO_ANSWER` cases cannot be called over-refusal solely from the reason code;
the retrieved evidence and final semantic grading must be considered separately.
No prompt tuning, retries or gate relaxation was introduced on this exposed QA.

`demo.local_demo` provides the real two-question classroom entry point, pins the
confirmed local model/endpoint, refuses API embeddings, shows both exported quotes
and complete source chunks, and restores its temporary environment settings.
The agent ran both real examples successfully. Full offline tests reported 335
passed and 2 skipped; Ruff and diff checks passed. The 36-answer grading artifact
was checked unchanged by SHA-256. These tools were first validated independently;
the unified delivery branch now includes the full-citation and runtime changes.

### Technical explanation for the report

The generation stage receives the question and retrieved source chunks and asks
the model to cite exact chunk identifiers for each claim. Empty retrieval,
explicit insufficient-evidence output and failed citation/coverage checks produce
an abstention while retaining raw model output for developer diagnosis. Source
membership and verbatim quote checks establish traceability, not factual support.
For example, a model can omit citations despite producing a plausible answer,
or cite a real but irrelevant chunk. Human semantic grading therefore remains
separate from structural checks. The prefix-only quote export additionally
demonstrated that an answer artifact can omit evidence that was visible to the
model; the complete-chunk export fix originated in #25 and is included here. Its
code version must be identified when comparing runs. Preserving original runs and explicit new
run IDs prevents an engineering fix from silently changing the evaluation input.
## Real local Ollama integration (2026-11-22)

The user reported that the team agreed to local Ollama `qwen3:4b-instruct` in
the working conversation; no separate GitHub decision link was supplied. This
supersedes earlier C3-pending notes for this local setup. No paid API is used.
The independent Python 3.11 environment and commands are in `demo/OLLAMA.md`;
`demo/ollama.toml` leaves shared configuration unchanged and uses a separate
T5 index directory. Source hashes for all 16 frozen documents were verified,
and T4's `validate --require-reviewed` passed for the integrated 36-item QA.

Actual agent execution built 668 fixed chunks (600/80, top_k=3, min_score=0.0).
A real K01 CLI request returned the control plane and worker nodes with
`[k8s_v135_components#0000]`; citation ID and verbatim structure checks passed.
A real KN01 CLI request refused with `model_reported_insufficient_evidence`.
These are observed behaviors, not independent human grades or correctness rates.
That baseline's exported prefix can omit supporting text; the integrated exporter
now preserves full chunks for new outputs. This does not alter the old baseline.

The original Conda Python 3.12 environment crashed importing ONNX. Independent
Python 3.11.18 with Chroma 1.5.9 and ONNX Runtime 1.32.0 successfully ingested
and ran the full offline suite: 195 passed, 2 skipped. Ruff and diff checks
passed. This does not establish that other Windows environments are repaired.
The local SDK also needed process-only `NO_PROXY` for localhost. No T3 source,
QA labels or human signatures were changed. Raw command logs stay local.

The local-model batch then completed with exit 0 for all 36 frozen QA rows.
The JSONL, sidecar and model/runtime provenance are in the ignored directory
`eval/results/raw/ollama-20261122/`. T4 loading, qid completeness, run references,
input hashes and citation structure against the reopened index all passed.
The handoff is ready for T4; independent semantic grading remains pending.
No correctness, retrieval or abstention metric is computed by this T5 work.
## Full citation export validation (2026-11-22)

Generation now exports the entire cited retrieved chunk rather than a 200-character
prefix, retaining the existing Answer/Citation and I4 fields. No gold answer or
gold quote is used to select or expand the exported text. Refusal gates and model
prompts are unchanged. The tradeoff is larger answer artifacts and more source
text for a judge to inspect; complete text still does not prove semantic support.
The CLI's short display preview is not the JSONL quote.

Synthetic English and Chinese regressions place the supporting sentence after
character 200, preserve boundary whitespace, and check the generated Answer,
nested JSONL and T4 loader. Agent execution on integrated main (including T3 PR
#11) reported 330 passed and 2 skipped for the full offline suite; Ruff and
`git diff --check` passed.

A separate real local Ollama smoke run exported K01 and KN01 with new run ID
`LOCAL-full-citations-smoke-20261122`. K01's exported citation matched all 600
characters of the stored chunk; KN01 still abstained. These two questions-only
inputs are smoke material, not a new gold set or formal evaluation. Raw output,
sidecar and verification record are in `eval/results/raw/full-citations-20261122/`.
The original 36-answer grading artifact's SHA-256 was checked unchanged. Existing
grades and reviewer packets were not regenerated. No semantic grades or new
correctness/abstention metrics were produced.

## Unified delivery acceptance (2026-11-22)

The delivery branch incorporates the exact #22/#24/#25 commits into #26 by
ordinary merges, preserving the original #25 approved commit. Only T5 conflicts
were resolved; both sides' added tests and execution records were retained.
Current integration notes above replace the outdated pending-state descriptions
from those branches. Unified offline validation: 340 passed / 2 skipped, Ruff
passed, and the enhanced MOCK export/loader check passed.

The agent also ran all 36 questions with fresh ID `LOCAL-full-citations-20261122`.
T4 loading, qid completeness, configuration/input hashes and structural citation
checks passed against the 668-chunk index. Every exported citation equalled its
entire stored chunk, with evidence beyond character 200 retained. The original
baseline remained unchanged by hash. New raw artifacts and model/runtime
provenance stay ignored under `eval/results/raw/t5-unified-20261122/`.
This engineering regression does not replace existing human-rating inputs and
is not an independent blind benchmark. No semantic grades, agreement statistic
or correctness/abstention metric is supplied by this T5 work.

## PR #18 review fixes (2026-11-21)
MOCK batch exports now build their provenance snapshot without loading the REAL configuration or reading its manifest. The MOCK snapshot records the synthetic pipeline's actual `min_score=0.0` instead of inheriting a value from `config.toml`. A regression test supplies a missing REAL manifest and a conflicting retrieval threshold, then verifies that the MOCK export still succeeds and records the fixture pipeline values. Validation after these fixes: 45 generation/offline pipeline tests passed, the suite excluding the known Windows Chroma store crash passed with 3 skips, and Ruff plus `git diff --check` passed. No paid API calls were made.
