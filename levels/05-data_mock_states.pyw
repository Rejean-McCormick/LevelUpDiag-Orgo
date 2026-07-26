# -*- coding: utf-8 -*-
"""LevelUpDiag N05 — Data & Mock States."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N05"
LEVEL_NAME = "Data & Mock States"
PURPOSE = "Tester fixtures, empty/error/slow/malformed si configurés."

def run_checks(config, report, log):

    fixture_dir = config.path("mocks.fixture_dir")
    if fixture_dir.exists():
        report.add("mocks.fixture_dir", PASS, "mocks", f"Fixture dir trouvé: {fixture_dir}")
    else:
        report.add("mocks.fixture_dir", WARN, "mocks", f"Fixture dir absent: {fixture_dir}", recommendation="Ajouter fixtures ou adapter ce niveau dans /levels")
    for state in config.get("mocks.states", []) or []:
        report.add(f"mock.state.{state}", SKIP, "mocks", f"État mock déclaré mais test spécifique à implémenter: {state}")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
