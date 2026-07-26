# -*- coding: utf-8 -*-
"""LevelUpDiag N14 — Release Gate."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N14"
LEVEL_NAME = "Release Gate"
PURPOSE = "Agréger les rapports et décider GO/NO-GO."

def run_checks(config, report, log):

    reports = sorted(config.artifacts_root_path.rglob("*-report.json"))
    if not reports:
        report.add("release.reports.none", WARN, "release", "Aucun rapport de niveau trouvé", recommendation="Lancer les niveaux précédents avant N14")
    else:
        fail_like = []
        import json
        for p in reports:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                verdict = data.get("verdict", "ERROR")
                if verdict in {"FAIL", "ERROR", "INFRA_ERROR", "CONFIG_ERROR", "BLOCKED"}:
                    fail_like.append((str(p), verdict))
            except Exception as exc:
                fail_like.append((str(p), f"unreadable:{exc}"))
        report.add("release.reports.count", PASS, "release", f"{len(reports)} rapports trouvés")
        if fail_like:
            report.add("release.no_go", FAIL, "release", f"{len(fail_like)} rapport(s) bloquants", data={"fail_like": fail_like})
        else:
            report.add("release.go", PASS, "release", "Aucun rapport bloquant trouvé")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
