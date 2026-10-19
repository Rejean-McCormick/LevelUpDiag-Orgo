from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .manifest import ManifestError, load_manifest, level_map
from .runner import run_campaign
from .util import read_json
from .worker import run_worker
from .evidence_integrity import EvidenceError, digest_file, verify_campaign_evidence, MAX_SUMMARY_BYTES


def parser():
    p = argparse.ArgumentParser(prog="levelupdiag", description="Standalone LevelUpDiag-Orgo")
    p.add_argument("--target", help="Separate Orgo repository root; required unless configured locally")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="Validate LevelUpDiag setup and target resolution")
    sub.add_parser("list", help="List levels and campaigns")
    sub.add_parser("show-config", help="Print effective configuration")
    r = sub.add_parser("run", help="Run a campaign or level")
    r.add_argument("selection", nargs="?", default="standard")
    r.add_argument("--jobs", type=int, help="Maximum parallel level workers")
    r.add_argument("--fail-fast", action="store_true")
    v = sub.add_parser("verify-run", help="Verify a run, all level reports, SHA-256 links and verdict")
    v.add_argument("summary", help="Original .levelupdiag/runs/<run-id>/summary.json (not latest)")
    v.add_argument("--expected-summary-sha256", help="External SHA-256 pin from a trusted ledger")
    w = sub.add_parser("_worker", help=argparse.SUPPRESS)
    w.add_argument("--level", required=True); w.add_argument("--run-id", required=True)
    w.add_argument("--output", required=True); w.add_argument("--target", required=True, dest="worker_target")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    tool_root = Path(__file__).resolve().parents[1]
    try:
        if args.cmd == "_worker":
            data = run_worker(tool_root, args.level, args.run_id, Path(args.output), args.worker_target)
            return 0 if data.get("verdict") in {"PASS","WARN","SKIP","PARTIAL"} else 1
        manifest = load_manifest(tool_root)
        if args.cmd == "doctor":
            cfg = load_config(tool_root, args.target)
            print("LevelUpDiag doctor: PASS")
            print(f"tool_root:   {tool_root}")
            print(f"target_root: {cfg['_target_root']}")
            print(f"control_dir: {cfg['_control_root']}")
            print(f"levels:      {len(manifest['levels'])}")
            return 0
        if args.cmd == "list":
            print("Levels:")
            for x in sorted(manifest["levels"], key=lambda y:(y.get("order",0),y["id"])):
                req = "required" if x.get("required") else "optional"
                print(f"  {x['id']}  {x['name']} [{req}]")
            print("Campaigns:")
            for name, c in manifest.get("campaigns",{}).items():
                print(f"  {name}: {', '.join(c.get('levels',[]))}")
            return 0
        if args.cmd == "show-config":
            cfg = load_config(tool_root, args.target)
            print(json.dumps({k:v for k,v in cfg.items() if not k.startswith('_')}, indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "run":
            summary, code, run_root = run_campaign(tool_root, args.selection, args.target, args.jobs, args.fail_fast)
            print(f"LevelUpDiag {args.selection}: {summary['verdict']}")
            for row in summary["levels"]:
                print(f"  {row['id']}  {row['verdict']:<12} {row['name']}")
            print(f"Report: {run_root / 'summary.json'}")
            print(f"Summary SHA-256 (pin externally): {digest_file(run_root / 'summary.json', MAX_SUMMARY_BYTES)}")
            return code
        if args.cmd == "verify-run":
            summary, sha = verify_campaign_evidence(Path(args.summary), args.expected_summary_sha256)
            print(f"VALID: {summary['verdict']} / {len(summary['levels'])} level reports / SHA-256 {sha}")
            if not args.expected_summary_sha256:
                print("NOTE: Integrity verified, but not independently authenticated. Pin the summary SHA-256 externally.")
            return 0
        return 64
    except (ConfigError, ManifestError, EvidenceError, OSError, ValueError) as e:
        print(f"LevelUpDiag error: {e}", file=sys.stderr)
        return 30
