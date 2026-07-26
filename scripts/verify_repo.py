"""Verify LevelUpDiag repository structure. Dependency-free except stdlib."""
from __future__ import annotations
import argparse, json, py_compile, sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOT = ["README.md", "levelupdiag_manifest.json", "levelupdiag.config.example.json", "levelupdiag_wrapper.pyw", "levelupdiag_wrapper_common.py"]
REQUIRED_DIRS = ["levels", "levelupdiag_core", "scripts", "launchers", "docs", "schemas"]
REQUIRED_CORE = ["config.py", "manifest.py", "commands.py", "reports.py", "level_runner.py", "verdicts.py", "artifacts.py", "http.py", "__init__.py"]

@dataclass
class Check:
    name: str
    status: str
    detail: str = ""

def add(out, name, status, detail=""):
    out.append(Check(name, status, detail))

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    checks: list[Check] = []
    for rel in REQUIRED_ROOT:
        add(checks, f"root.file:{rel}", "PASS" if (ROOT/rel).is_file() else "FAIL")
    for rel in REQUIRED_DIRS:
        add(checks, f"root.dir:{rel}", "PASS" if (ROOT/rel).is_dir() else "FAIL")
    for rel in REQUIRED_CORE:
        add(checks, f"core.file:{rel}", "PASS" if (ROOT/"levelupdiag_core"/rel).is_file() else "FAIL")
    try:
        manifest = json.loads((ROOT/"levelupdiag_manifest.json").read_text(encoding="utf-8"))
        add(checks, "manifest.json", "PASS")
        ids = [x.get("id") for x in manifest.get("levels", [])]
        add(checks, "manifest.levels.count", "PASS" if ids else "FAIL", str(len(ids)))
        for item in manifest.get("levels", []):
            lf = ROOT / str(item.get("file", ""))
            add(checks, f"level.exists:{item.get('id')}", "PASS" if lf.is_file() else "FAIL", str(lf))
    except Exception as exc:
        add(checks, "manifest.json", "FAIL", str(exc))
    for py in list((ROOT/"levelupdiag_core").glob("*.py")) + list((ROOT/"scripts").glob("*.py")):
        try:
            py_compile.compile(str(py), doraise=True)
            add(checks, f"compile:{py.relative_to(ROOT)}", "PASS")
        except Exception as exc:
            add(checks, f"compile:{py.relative_to(ROOT)}", "FAIL", str(exc))
    fail_count = sum(1 for c in checks if c.status == "FAIL")
    if args.json:
        print(json.dumps({"fail_count": fail_count, "checks": [c.__dict__ for c in checks]}, indent=2, ensure_ascii=False))
    else:
        for c in checks:
            print(f"{c.status:5} {c.name} {c.detail}")
        print(f"FAIL count: {fail_count}")
    return 2 if fail_count else 0

if __name__ == "__main__":
    raise SystemExit(main())
