# T5 operational handoff

## Remaining ownership

T5 owns generation, refusal gates, citation export and the runnable demo. T4
owns gold/QA review, independent answer grading, adjudication and all metric
aggregation. T3 owns retrieval diagnosis and tuning. Do not replace an answer
batch while its grades are being collected.

## One-command real local demonstration

After the team's local Ollama choice has been confirmed and a matching index
prepared, run from the repository root with the project Python environment:

```powershell
python -m demo.local_demo --config PATH_TO_LOCAL_INDEX_CONFIG.toml
```

This executes two real questions using `qwen3:4b-instruct` on
`http://localhost:11434/v1`. The process pins that model, a dummy local SDK key
and localhost proxy exclusion, and restores those environment variables on exit.
It refuses API embedding configurations before constructing the pipeline. It
does not build/clear an index, select a cloud model, export grades or compute
metrics. Keep Ollama running with this model downloaded. A compatible config
recipe is in the separately reviewed local Ollama integration PR; do not assume
an open PR is already merged.

The display separates the actual exported quote from the complete retrieved
chunk. Older generation exports can contain only a 200-character prefix; the
full-citation fix is a separate T5 change. Neither source membership nor verbatim
text is a semantic verdict. A live model may abstain on either example; show the
actual response rather than substituting a prerecorded answer.

## Diagnose an existing I4 artifact without model calls

```powershell
python -m demo.inspect_answers --config PATH_TO_MATCHING_INDEX_CONFIG.toml --outputs PATH_TO_EXISTING.jsonl --report eval/results/raw/NEW-diagnostics.json
```

Use an unused report path and the index corresponding to the original run.
The script uses T4's existing loader and T5's existing gate/structure helpers.
It reports one record per answer: source hash, missing retrieved IDs, generator
gate, uncovered text units and structural citation validity. It does not load
gold, query embeddings, call an LLM, recompute retrieval scores, aggregate rates
or create human grades. Structural helpers receive placeholder scores that are
never evaluated or exported. Missing source chunks produce `incomplete_index`
with unknown gate/structure values rather than a guessed refusal explanation.

## Qualitative baseline cases

The old local-model artifact provides these diagnostic examples; they are not
test-set tuning instructions or semantic ratings:

- K06: the raw model output contains several sentences but cites only the last
  sentence. The `uncovered_claim` gate correctly rejects the preceding uncited
  sentences. This is a citation-compliance failure, not evidence that the gate
  should be weakened.
- K24: the raw model output is a command without a citation. The
  `missing_citations` gate correctly rejects it.
- K02/K03 and other `NO_ANSWER` cases: the model reports insufficient evidence.
  This signal alone cannot distinguish missing retrieval evidence from model
  over-refusal. Hand the matching context and run configuration to T3/T4 for
  their respective diagnosis and grading; do not call every refusal a T5 bug.

## Final delivery checklist

- Keep the original JSONL, sidecar and model/runtime provenance together; raw
  data and indices stay out of Git. Preserve qids and original hashes.
- Keep baseline, citation-fix smoke runs and any future runs under separate IDs.
  Engineering regression on exposed QA is not an independent blind benchmark.
- Give T4 the matching artifact and contextual limitations; collect two actual
  independent human grade files and adjudication through their protocol. AI
  preparation or AI pre-review is not a human signature or second rater.
- Keep generator diagnostics, raw rejected model outputs and model-identifying
  demo material out of the independent raters' packets until initial ratings
  are complete; those are developer/coordinator materials, not grading inputs.
- The code author should personally review/rerun the commands. Another member
  reviews and merges T5 PRs under CONTRIBUTING.md. Issue #5 stays open until the
  team verifies its remaining delivery requirements.

## Verified execution on 2026-11-22

The agent ran the inspector on the original 36-answer local artifact using its
matching T5 index. All retrieved IDs resolved; K06 reproduced `uncovered_claim`
with two uncovered units and K24 reproduced `missing_citations`. The original
answer file still matched the SHA-256 recorded when the review packets were
prepared. Per-answer diagnostics are local at
`eval/results/raw/t5-diagnostics-20261122/baseline-diagnostics.json`.

The real local demo then ran both examples, displaying a cited cluster-components
answer and an insufficient-evidence refusal. Its log stays in that raw directory.
This branch is based on integrated main and does not bundle the still-open
full-citation export fix: the observed exported prefix and the complete retrieved
source were therefore displayed separately. No new formal batch or grades were
created. Full offline pytest: 335 passed, 2 skipped. Ruff passed. These commands
were agent execution, not a personal human rerun or independent grading.
