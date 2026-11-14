## What changed

<!-- One or two sentences. Say WHICH module you touched (M1..M5 or shared).
     Project definition, task cards and the dependency schedule:
     docs/PROJECT_PLAN.md and docs/TASKS.md. -->

## Why

<!-- What problem does this solve? Link the issue if there is one. -->

## Self-check (tick before requesting review)

- [ ] I only changed files listed in my task package (see `docs/TASKS.md`), plus my own tests.
- [ ] My reviewer is **another group member**, not the PR author.
- [ ] `ci / check` is green (this plan cannot enforce protection rules; I checked manually).
- [ ] If I used a Coding Agent, I reviewed the code myself and logged it in `docs/AI_USAGE.md`.
- [ ] I ran `python -m pytest -q` locally and it passed.
- [ ] I ran `ruff check .` locally and it passed.
- [ ] I did NOT commit `.env`, API keys, `data/index/`, or `eval/results/raw/`.
- [ ] Any committed experiment summary in `eval/results/summary/` comes from a real run and includes command, config, date and frozen-input ids (see `eval/results/README.md`).
- [ ] If I changed a field in `ragkit/contracts.py`, I asked for **2** reviews and told the group.
- [ ] If I changed `config.toml` or `requirements*.txt`, I told the group (affects everyone).
- [ ] Any new behaviour has a test, and MOCK tests are clearly labelled MOCK.
- [ ] I did not hard-code any evaluation number or claim a run I did not perform.

## How a reviewer can verify

<!-- Exact command to run, and the expected output. Keep it copy-pasteable. -->

## Notes for the report (optional)

<!-- Anything that should go into methodology / contribution statement. -->
