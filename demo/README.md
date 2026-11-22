# Offline T5 demo

Run from the repository root with Python 3.11 or newer.

```powershell
python -m demo.run
python -m demo.validate_export
python -m ragkit.cli batch --mock --questions demo/questions.csv --run-id MOCK-example --output eval/results/raw/MOCK-example.jsonl
```

Synthetic fixtures and scripted responses require no API key. The demo displays a normal answer with its source excerpt and two refusal cases. Choose a new output path when repeating a batch run. Citation structure does not establish semantic support. Real LLM integration remains pending team API approval.

`demo.validate_export` performs an offline T5-to-T4 handoff smoke check: it exports
the two synthetic questions, reads them with T4's existing `load_outputs`, checks
the expected question IDs, scripted answer/refusal states, retrieved citation IDs,
configuration references and input hashes, and removes its temporary artifacts on exit. It
does not calculate metrics or use the formal QA dataset.

## Classroom walkthrough (MOCK, about three minutes)

1. Announce that this uses synthetic documents, scripted model responses and an
   in-memory store. It demonstrates generation safeguards, not real retrieval
   quality or an LLM's reasoning ability.
2. Run `python -m demo.run`. For the normal answer, point to the inline chunk ID
   and source excerpt. Explain three separate questions: did this turn retrieve
   the cited ID, is the excerpt verbatim, and does the excerpt support the claim?
   Only the first two are checked structurally; semantic grading belongs to T4.
3. Show the fabricated-ID refusal and insufficient-evidence refusal. A refusal
   describes generator behavior; whether it was appropriate requires gold data
   and independent grading. A provider/network exception is an execution error.
4. Run the MOCK batch command above with an unused run ID and output filename.
   Open the JSONL and adjacent `.config.json`. Show `qid`, nested `answer`,
   `retrieved_chunk_ids`, `run_id` and `config_ref`, then the sidecar's MOCK mode,
   synthetic settings and input hashes. These hashes identify bytes; they do not
   certify frozen data, correctness or human review.

## Before a REAL demonstration

- Confirm the team's C3 API/provider and cost decision. The offline commands
  above do not authorize a real call.
- Verify the integrated corpus snapshot, matching index and frozen QA with
  their owners. An open PR is not an integrated dependency.
- Check the selected configuration's chunking, embedding, collection, retrieval
  and LLM settings against the index and agreed experiment settings. Keep
  credentials outside submitted artifacts.
- After approval, use `python -m ragkit.cli --config APPROVED.toml ask "QUESTION"`
  for the live example. Use `batch` without `--mock` only for an approved real
  run, with a fresh output path. Preserve the JSONL and sidecar together.
- Hand the answers to T4 for independent semantic grading and metric aggregation.
  Do not report MOCK behavior as real performance or fill in reviewer signatures.

If real prerequisites are unavailable, use the MOCK walkthrough and state the
missing dependency explicitly. Do not present an offline transcript as a real run.
