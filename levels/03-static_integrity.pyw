# -*- coding: utf-8 -*-
"""LevelUpDiag N03 — Static Integrity."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N03"
LEVEL_NAME = "Static Integrity"
PURPOSE = "Vérifier structure fichiers, manifest, config, commandes statiques."

def run_checks(config, report, log):

    log("Vérification intégrité statique")
    for key in ["paths.frontend_dir", "paths.backend_dir", "paths.package_json", "paths.pyproject"]:
        p = config.path(key)
        exists = p.exists()
        severity = PASS if exists else WARN
        report.add(key, severity, "static", f"{p} {'existe' if exists else 'absent'}")
    for cmd_key in ["lint", "typecheck", "test", "build"]:
        cmd = str(config.get(f"commands.{cmd_key}", "")).strip()
        if not cmd:
            report.add(f"command.{cmd_key}.missing", SKIP, "static", f"commands.{cmd_key} non configurée")
            continue
        log(f"Run {cmd_key}: {cmd}")
        result = run_cmd(cmd, cwd=config.target_root_path, timeout=180, env=config.env(), name=cmd_key)
        report.add(f"command.{cmd_key}", result.status, "static", f"{cmd_key}: exit={result.exit_code}", evidence=result.output_tail, data=result.to_dict())

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
