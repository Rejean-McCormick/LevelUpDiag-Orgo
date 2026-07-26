"""Launch a LevelUpDiag level from levelupdiag_manifest.json.

Usage:
  py scripts/run_level.py --list
  py scripts/run_level.py N04
  py scripts/run_level.py 4 --wait
  py scripts/run_level.py N04 --windowed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from levelupdiag_core.config import load_config
from levelupdiag_core.manifest import get_level, list_levels, normalize_level_id
from levelupdiag_wrapper_common import find_python_console, find_python_windowed


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch a LevelUpDiag level.")
    parser.add_argument("level", nargs="?", help="N00..N15, 0..15, or LUD-00")
    parser.add_argument("--list", action="store_true", help="list available levels")
    parser.add_argument("--wait", action="store_true", help="wait for the launched level to exit")
    parser.add_argument("--windowed", action="store_true", help="use pythonw/pyw when available")
    parser.add_argument("--console", action="store_true", help="use console Python")
    args = parser.parse_args()

    if args.list or not args.level:
        for item in list_levels(ROOT):
            print(f"{item.id}  {item.file}  - {item.name}")
        return 0

    level_id = normalize_level_id(args.level)
    try:
        item = get_level(level_id, ROOT)
    except KeyError:
        print(f"Unknown level: {args.level}", file=sys.stderr)
        return 2

    path = ROOT / item.file
    if not path.exists():
        print(f"Missing file: {path}", file=sys.stderr)
        return 3

    cfg = load_config(root=ROOT)
    exe = find_python_windowed() if args.windowed and not args.console else find_python_console()
    proc = subprocess.Popen([exe, str(path)], cwd=str(ROOT), env=cfg.env())
    print(f"Launched {item.id}: {path}")
    if args.wait:
        return int(proc.wait())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
