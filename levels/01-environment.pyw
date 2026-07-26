# -*- coding: utf-8 -*-
"""LevelUpDiag N01 — Environment."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N01"
LEVEL_NAME = "Environment"
PURPOSE = "Vérifier machine, outils, chemins, config locale."

def run_checks(config, report, log):

    log("Vérification environnement")
    if config.target_root_path.exists():
        report.add("target.root.exists", PASS, "environment", f"Target repo trouvé: {config.target_root_path}")
    else:
        report.add("target.root.missing", CONFIG_ERROR, "environment", f"Target repo introuvable: {config.target_root_path}", recommendation="Corriger target_repo_root dans la config locale")
    for tool in config.get("toolchain.required", []) or []:
        exe = find_executable(str(tool))
        if exe:
            report.add(f"tool.required.{tool}", PASS, "toolchain", f"{tool} trouvé", evidence=exe)
        else:
            report.add(f"tool.required.{tool}", FAIL, "toolchain", f"{tool} introuvable", recommendation="Installer l’outil ou retirer de toolchain.required")
    for tool in config.get("toolchain.optional", []) or []:
        exe = find_executable(str(tool))
        report.add(f"tool.optional.{tool}", PASS if exe else WARN, "toolchain", f"{tool}: {exe or 'introuvable'}")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
