# Provenance of this summary (interface I4, first REAL answer run)

T4's official metric aggregation over T5's local Ollama answers. Everything in
`config.json` / `metrics.json` / `run.md` here was produced by the command
recorded in `run.md`; no number in this directory is typed in by hand.

## What the input is, and why it is not in Git

The scored artifact is `LOCAL-ollama-fixed-20261122.jsonl` (36 records), handed
to T4 as `T5-Ollama-I4-handoff-20261122.zip`. **It is deliberately not
committed**: the producing task wrote in `T5-OLLAMA-HANDOFF.md` that "Raw files
and this ZIP must not be committed to Git", and T4 does not move another
task's product into the repository on their behalf. Consequence to state
plainly: the `command:` line in `run.md` only runs on a machine that holds the
handoff ZIP, so this summary is *verifiable by hash*, not yet *reproducible by
CI*. The repo-native fix is for T5 to place the file at
`eval/answers/<run_id>.jsonl` (the path `eval/judge_protocol.md`,
`docs/TASKS.md` T5 and `--run-id` all name); from then on
`python -m eval.metrics score --run-id LOCAL-ollama-fixed-20261122 --formal`
replaces the `--outputs` path.

SHA-256 of the inputs as received by T4 on 2026-11-22:

| file | sha256 |
| --- | --- |
| `T5-Ollama-I4-handoff-20261122.zip` (8193 B) | `c464299a231e59130f22360c57549fb2ce1ceef284b813efa8d49a3367d4bd85` |
| `LOCAL-ollama-fixed-20261122.jsonl` | `2ca74fde05a52da95c1c0b7b712ddea38ed20ce2a78cdac23775cb1b96346076` |
| `LOCAL-ollama-fixed-20261122.config.json` | `7793aebe4863af598777f559637fad9b27a4f89fb17e47fbf8e6f56ebb36d19a` |
| `run.json` (T5's own execution record) | `a09700afd39235b140ccd8876e92e03fbef87fbdc665fedc60656318402464c8` |
| `handoff_check.json` | `3ee0c1f919840dcb46dab16a64f231745a09f191fe8888f93595c0ad364aded3` |
| `local-config.toml` = `demo/ollama.toml` @ PR #24 | `51ecccc7ff978519caf645059e48819c7fa722c332716da1424ad583225e0f37` |

## Bindings T4 re-computed rather than trusted

- QA set: `eval/qa_set.csv@b01b97fbdf2a` (I2, 36 items) - matches `run.json.qa_sha256`.
- Corpus: `cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885` (I1 frozen) - matches
  `run.json.frozen_manifest_sha256`; 12 of 16 snapshot documents carry gold.
- Index: T4 rebuilt the chunker from the frozen snapshot and reproduced
  **668 chunks**, equal to `handoff_check.json.index_chunks`.
- Citations: all 12 quoted spans re-found verbatim inside the cited chunk.
- `run.json.source_commit = 1963537` = `origin/main` when T5 ran (so the run is
  bound to the merged I2, not to a branch commit).

## Who ran what

| step | executor |
| --- | --- |
| answering (36 records, 261 s) | `run.json.executor`: "Codex agent; not a personal human rerun" |
| this scoring run | `run.md.executor`: coding agent on the T4 workstation; human rerun pending |
| semantic grading | **not done** - `answer_correctness = pending human grading`, `grading_coverage 0/26` |

## Reading the numbers honestly

- `correct_abstention_rate 10/10` is the only answer metric with a full
  denominator, and it rests on the 10 `REVIEWED_BY` signatures in `eval/qa_set.csv`.
- `false_abstention_rate 14/26 = 0.5385`: 14 answerable questions were refused.
  12 questions were answered at all.
- `answer_correctness` takes its denominator from the answerable items a judge
  graded, so the two are coupled: grading all 26 caps correctness at
  `12/26 = 0.4615` (the protocol scores an evasive answer as incorrect), while
  grading only the 12 answered questions can reach `1.0` but drops
  `grading_coverage` to `12/26 = 0.4615`, which `eval/judge_protocol.md` calls a
  smoke test, not a result. Report the pair, never correctness alone.
- `citation_structure_rate 12/12` is a structural check (valid ids, verbatim
  quote, citation present). It is not, and must never be quoted as, factual
  correctness.

## Next step that belongs to people, not to this script

Two raters who did not write the questions grade the 26 answerable rows
independently (an evasive answer counts as `incorrect`, so a refusal is graded,
not skipped). Their two sheets are then reconciled into **one** csv under
`eval/review/` - `score --grades` accepts exactly one file and exits 2 on a
repeated flag, precisely so that a single person's sheet cannot be published as
an agreement. Re-run the command in `run.md` with
`--grades eval/review/grades_LOCAL-ollama-fixed-20261122.csv` and report
inter-rater agreement next to the rate, by hand, per `eval/judge_protocol.md`
§2. Until then this directory is a complete record of an *ungraded* run.
