# -*- coding: utf-8 -*-
"""LevelUpDiag N06 — Runtime Smoke."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N06"
LEVEL_NAME = "Runtime Smoke"
PURPOSE = "Charger l’app réelle et détecter erreurs runtime minimales."

def run_checks(config, report, log):

    res = get(config.frontend_url, timeout=8)
    report.add("runtime.frontend.load", PASS if res.ok else FAIL, "runtime", f"Frontend load: {res.status or res.error}", data=res.__dict__)

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
