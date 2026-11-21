"""Run from repository root with python -m demo.run. MOCK only."""
from ragkit.cli import cmd_offline_demo

if __name__ == '__main__':
    raise SystemExit(cmd_offline_demo(None))
