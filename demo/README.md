# Offline T5 demo

Run from the repository root with Python 3.11 or newer.

```powershell
python -m demo.run
python -m ragkit.cli batch --mock --questions demo/questions.csv --run-id MOCK-example --output eval/results/raw/MOCK-example.jsonl
```

Synthetic fixtures and scripted responses require no API key. The demo displays a normal answer with its source excerpt and two refusal cases. Choose a new output path when repeating a batch run. Citation structure does not establish semantic support. Real LLM integration remains pending team API approval.
