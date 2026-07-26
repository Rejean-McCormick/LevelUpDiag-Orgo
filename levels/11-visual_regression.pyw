# -*- coding: utf-8 -*-
"""LevelUpDiag N11 — Visual Regression."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N11"
LEVEL_NAME = "Visual Regression"
PURPOSE = "Comparer captures baseline/current/diff."

def run_checks(config, report, log):

    report.add("visual.template", SKIP, "visual", "Niveau à brancher sur baseline/current/diff screenshots", recommendation="Définir routes et seuils de diff visuel")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
