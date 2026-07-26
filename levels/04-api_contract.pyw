# -*- coding: utf-8 -*-
"""LevelUpDiag N04 — API Contract."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N04"
LEVEL_NAME = "API Contract"
PURPOSE = "Vérifier OpenAPI ou contrat HTTP configuré."

def run_checks(config, report, log):

    log("Vérification contrat API")
    found = False
    for path in config.get("api.openapi_paths", []) or []:
        url = config.backend_url + str(path)
        res, data = get_json(url, timeout=5)
        log(f"{url} -> {res.status or res.error}")
        if res.ok and isinstance(data, dict):
            found = True
            paths = data.get("paths", {}) if isinstance(data.get("paths"), dict) else {}
            report.add("openapi.fetch", PASS, "api", f"OpenAPI trouvé avec {len(paths)} paths", endpoint=url)
            break
        else:
            report.add(f"openapi.try.{path}", WARN, "api", f"OpenAPI non disponible: {url}", evidence=res.error)
    openapi_file = config.path("paths.openapi_file")
    if not found and openapi_file.exists():
        report.add("openapi.file", PASS, "api", f"OpenAPI local trouvé: {openapi_file}")
        found = True
    if not found:
        report.add("openapi.missing", FAIL, "api", "Aucun contrat OpenAPI accessible", recommendation="Configurer api.openapi_paths ou paths.openapi_file")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
