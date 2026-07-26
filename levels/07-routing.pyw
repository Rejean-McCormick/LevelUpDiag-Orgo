# -*- coding: utf-8 -*-
"""LevelUpDiag N07 — Routing."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N07"
LEVEL_NAME = "Routing"
PURPOSE = "Tester routes critiques configurées."

def run_checks(config, report, log):

    for route in config.get("routes.critical", []) or []:
        url = config.frontend_url + str(route)
        res = get(url, timeout=8)
        log(f"{url} -> {res.status or res.error}")
        report.add(f"route.{route}", PASS if res.ok else FAIL, "routing", f"Route {route}: {res.status or res.error}", route=str(route), data=res.__dict__)

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
