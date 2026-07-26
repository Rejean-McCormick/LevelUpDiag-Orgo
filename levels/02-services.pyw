# -*- coding: utf-8 -*-
"""LevelUpDiag N02 — Services."""
from __future__ import annotations

from pathlib import Path
from levelupdiag_core.level_runner import run_level_app
from levelupdiag_core.verdicts import PASS, WARN, FAIL, SKIP, INFRA_ERROR, CONFIG_ERROR
from levelupdiag_core.commands import find_executable, run_cmd, launch_console
from levelupdiag_core.http import get, get_json

LEVEL_ID = "N02"
LEVEL_NAME = "Services"
PURPOSE = "Tester backend/frontend/health endpoints configurés."

def run_checks(config, report, log):

    log("Vérification services HTTP")
    frontend = get(config.frontend_url, timeout=5)
    report.add("frontend.http", PASS if frontend.ok else WARN, "services", f"Frontend {config.frontend_url}: {frontend.status or frontend.error}", data=frontend.__dict__)
    backend_any = False
    for path in config.get("api.health_paths", []) or []:
        url = config.backend_url + str(path)
        res = get(url, timeout=4, accept="application/json")
        log(f"{url} -> {res.status or res.error} ({res.duration_ms} ms)")
        if res.ok:
            backend_any = True
            report.add(f"backend.health.{path}", PASS, "services", f"OK {url}", data=res.__dict__)
        else:
            report.add(f"backend.health.{path}", WARN, "services", f"Non OK {url}: {res.status or res.error}", data=res.__dict__)
    if not backend_any:
        report.add("backend.health.none", FAIL, "services", "Aucun health endpoint backend n’a répondu OK", recommendation="Corriger backend_url ou api.health_paths")

if __name__ == "__main__":
    run_level_app(LEVEL_ID, LEVEL_NAME, PURPOSE, run_checks)
