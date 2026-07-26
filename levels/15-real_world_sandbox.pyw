# -*- coding: utf-8 -*-
"""LevelUpDiag N15 — Real-World Sandbox."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N15"
LEVEL_NAME = "Real-World Sandbox"
PURPOSE = "Valider un scénario réaliste mais contrôlé/sandboxé."

def run_checks(config, report, log):

    report.add("sandbox.template", SKIP, "sandbox", "Niveau produit réel à adapter dans /levels", recommendation="Utiliser seulement des données sandbox/autorisées")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
