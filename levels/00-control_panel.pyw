# -*- coding: utf-8 -*-
"""LevelUpDiag N00 — Control Panel."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N00"
LEVEL_NAME = "Control Panel"
PURPOSE = "Démarrer/arrêter/ouvrir les services locaux via commandes de config."

def run_checks(config, report, log):

    log("Control panel basé sur levelupdiag.config.local.json")
    commands = config.get("commands", {{}}) or {{}}
    backend = str(commands.get("backend_start", "")).strip()
    frontend = str(commands.get("frontend_start", "")).strip()
    if backend:
        log(f"Commande backend disponible: {backend}")
        report.add("command.backend_start.configured", PASS, "config", "backend_start est configuré")
    else:
        report.add("command.backend_start.missing", WARN, "config", "Aucune commande backend_start configurée", recommendation="Ajouter commands.backend_start dans levelupdiag.config.local.json")
    if frontend:
        log(f"Commande frontend disponible: {frontend}")
        report.add("command.frontend_start.configured", PASS, "config", "frontend_start est configuré")
    else:
        report.add("command.frontend_start.missing", WARN, "config", "Aucune commande frontend_start configurée", recommendation="Ajouter commands.frontend_start dans levelupdiag.config.local.json")
    log("Ce niveau est volontairement non destructif. Lancement de services à personnaliser si désiré.")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
