"""Offline I4 handoff smoke check. Run from repository root; no API calls."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from eval.metrics import load_outputs
from ragkit.cli import cmd_batch


def main() -> int:
    with TemporaryDirectory(prefix="ragkit-mock-handoff-") as directory:
        output = Path(directory) / "MOCK-handoff.jsonl"
        cmd_batch(argparse.Namespace(
            questions="demo/questions.csv", output=str(output),
            run_id="MOCK-handoff", config=None, mock=True,
        ))
        rows = load_outputs(output)
        if len(rows) != 2:
            raise RuntimeError("Expected both synthetic demo questions in T4 input")
        snapshot = json.loads(output.with_suffix(".config.json").read_text(encoding="utf-8"))
        if snapshot["mode"] != "MOCK" or snapshot["min_score"] != 0.0:
            raise RuntimeError("Unexpected MOCK provenance settings")
        print("[MOCK] PASS: two I4 records accepted by T4 load_outputs; snapshot checked.")
        print("Temporary artifacts removed on exit. This is not a formal evaluation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
