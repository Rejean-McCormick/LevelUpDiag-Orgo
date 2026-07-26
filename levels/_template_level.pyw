# -*- coding: utf-8 -*-
"""LevelUpDiag NXX — Template."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "NXX"
LEVEL_NAME = "Template"
PURPOSE = "Copier ce fichier pour créer un niveau app-specific."

def run_checks(config, report, log):

    report.add("template.started", PASS, "template", "Le template démarre correctement")
    # Ajouter ici les checks propres à votre app.

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
