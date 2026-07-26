# -*- coding: utf-8 -*-
"""LevelUpDiag N13 — Security."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N13"
LEVEL_NAME = "Security"
PURPOSE = "Vérifier contrôles sécurité applicatifs minimum."

def run_checks(config, report, log):

    patterns = config.get("security.forbidden_log_patterns", []) or []
    if not patterns:
        report.add("security.patterns.none", SKIP, "security", "Aucun pattern sécurité configuré")
    else:
        report.add("security.patterns.configured", PASS, "security", f"{len(patterns)} patterns interdits configurés")
    protected = config.get("security.protected_routes", []) or []
    for route in protected:
        report.add(f"security.protected_route.{route}", SKIP, "security", f"Route protégée déclarée: {route}", recommendation="Implémenter test auth/redirect dans ce niveau")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
