"""Offline I4 handoff smoke check. Run from repository root; no API calls."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from eval.metrics import load_outputs
from ragkit.cli import cmd_batch
from ragkit.config import ROOT


def validate_export(output: Path) -> None:
    """Check the known synthetic handoff, without grading formal answers."""
    rows = load_outputs(output)
    if set(rows) != {"MOCK01", "MOCK02"}:
        raise RuntimeError("Expected both synthetic demo question IDs in T4 input")
    snapshot_path = output.with_suffix(".config.json")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if (snapshot["mode"] != "MOCK" or snapshot["min_score"] != 0.0
            or snapshot["run_id"] != "MOCK-handoff"):
        raise RuntimeError("Unexpected MOCK provenance settings")
    for field, source in (("qa_sha256", ROOT / "demo/questions.csv"),
                          ("manifest_sha256", ROOT / "tests/fixtures/manifest.json")):
        if snapshot[field] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise RuntimeError(f"MOCK input hash mismatch: {field}")
    for qid, row in rows.items():
        if row["run_id"] != snapshot["run_id"] or row["config_ref"] != str(snapshot_path):
            raise RuntimeError(f"Broken configuration reference for {qid}")
    normal, refusal = rows["MOCK01"], rows["MOCK02"]
    if (normal["abstained"] is not False or "8080" not in normal["answer_text"]
            or not normal["citations"]):
        raise RuntimeError("Scripted normal answer did not survive the I4 handoff")
    for citation in normal["citations"]:
        if citation["chunk_id"] not in normal["retrieved_chunk_ids"]:
            raise RuntimeError("Scripted citation missing from retrieved IDs")
    if refusal["abstained"] is not True or refusal["citations"]:
        raise RuntimeError("Scripted refusal did not survive the I4 handoff")


def main() -> int:
    with TemporaryDirectory(prefix="ragkit-mock-handoff-") as directory:
        output = Path(directory) / "MOCK-handoff.jsonl"
        cmd_batch(argparse.Namespace(
            questions="demo/questions.csv", output=str(output),
            run_id="MOCK-handoff", config=None, mock=True,
        ))
        validate_export(output)
        print("[MOCK] PASS: two I4 records accepted by T4 load_outputs; snapshot checked.")
        print("Temporary artifacts removed on exit. This is not a formal evaluation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
