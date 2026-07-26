# -*- coding: utf-8 -*-
"""LevelUpDiag N09 — Error & Resilience."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N09"
LEVEL_NAME = "Error & Resilience"
PURPOSE = "Tester timeouts, 500, réseau lent, réponses invalides."

def run_checks(config, report, log):

    report.add("resilience.template", SKIP, "resilience", "Niveau à adapter aux erreurs réelles de l’app", recommendation="Tester backend down, timeout, 500, malformed JSON, token expiré")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
