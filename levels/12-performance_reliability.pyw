# -*- coding: utf-8 -*-
"""LevelUpDiag N12 — Performance & Reliability."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N12"
LEVEL_NAME = "Performance & Reliability"
PURPOSE = "Mesurer budgets de chargement, API, ressources, répétition."

def run_checks(config, report, log):

    for route in config.get("routes.smoke", []) or []:
        url = config.frontend_url + str(route)
        res = get(url, timeout=8)
        budget = int(config.get("budgets.page_load_ms", 3000))
        status = PASS if res.ok and res.duration_ms <= budget else WARN if res.ok else FAIL
        report.add(f"perf.route.{route}", status, "performance", f"{route}: {res.duration_ms} ms / budget {budget} ms", data=res.__dict__)

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
