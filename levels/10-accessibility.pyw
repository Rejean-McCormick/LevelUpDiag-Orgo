# -*- coding: utf-8 -*-
"""LevelUpDiag N10 — Accessibility."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N10"
LEVEL_NAME = "Accessibility"
PURPOSE = "Tester navigation clavier, labels, focus, règles WCAG de base."

def run_checks(config, report, log):

    report.add("a11y.template", SKIP, "accessibility", "Niveau à brancher sur Playwright/axe ou checks clavier propres à l’app", recommendation="Tester focus visible, labels, ordre tabulation, modals")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
