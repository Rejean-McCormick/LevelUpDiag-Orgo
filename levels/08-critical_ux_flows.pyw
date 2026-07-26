# -*- coding: utf-8 -*-
"""LevelUpDiag N08 — Critical UX Flows."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N08"
LEVEL_NAME = "Critical UX Flows"
PURPOSE = "Tester parcours utilisateur critiques propres à l’app."

def run_checks(config, report, log):

    flows = config.get("ux_flows", []) or []
    if not flows:
        report.add("ux_flows.none", SKIP, "ux", "Aucun flow UX configuré", recommendation="Adapter levels/08-critical_ux_flows.pyw pour l’app cible")
    for flow in flows:
        report.add(f"ux_flow.{flow}", SKIP, "ux", f"Flow déclaré mais implémentation à compléter: {flow}")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
