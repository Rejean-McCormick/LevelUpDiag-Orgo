"""Common helpers for the LevelUpDiag wrapper GUI.

Design goals inherited from Ariane_Diagnostics:
- keep the wrapper lightweight;
- do not import files from levels/;
- launch each level as a separate process;
- use levelupdiag_manifest.json as the source of truth;
- use levelupdiag.config.local.json for local app parameters.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_NAME = "LevelUpDiag Wrapper"
APP_VERSION = "0.2.0"
MANIFEST_FILENAME = "levelupdiag_manifest.json"
CONFIG_FILENAME = "levelupdiag.config.local.json"
CONTROL_DIRNAME = ".levelupdiag"

@dataclass(frozen=True, slots=True)
class LevelInfo:
    id: str
    name: str
    file: str
    purpose: str = ""
    requires_backend: bool = False
    requires_frontend: bool = False
    requires_playwright: bool = False
    blocking_for_release: bool = False
    raw: dict[str, Any] | None = None

    @property
    def display_title(self) -> str:
        return f"{self.id} — {self.name}"

    def file_path(self, root: str | Path) -> Path:
        return Path(root) / self.file

    def requirements_label(self) -> str:
        reqs: list[str] = []
        if self.requires_backend: reqs.append("backend")
        if self.requires_frontend: reqs.append("frontend")
        if self.requires_playwright: reqs.append("playwright")
        return ", ".join(reqs) if reqs else "aucun prérequis runtime"


def detect_diag_root() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def control_dir(root: Path) -> Path:
    p = root / CONTROL_DIRNAME
    (p / "diagnostics").mkdir(parents=True, exist_ok=True)
    return p


def normalize_level_id(value: str) -> str:
    raw = str(value or "").strip().upper().replace("LUD", "").replace("-", "")
    if raw.startswith("N"):
        raw = raw[1:]
    if raw.isdigit():
        return f"N{int(raw):02d}"
    return raw or "N00"


def load_config(root: Path) -> dict[str, Any]:
    local = root / CONFIG_FILENAME
    example = root / "levelupdiag.config.example.json"
    path = local if local.exists() else example
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(root: Path) -> Path:
    local = root / CONFIG_FILENAME
    return local if local.exists() else root / "levelupdiag.config.example.json"


def load_manifest(root: Path) -> list[LevelInfo]:
    path = root / MANIFEST_FILENAME
    if not path.exists():
        return scan_levels_folder(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    levels = []
    for item in data.get("levels", []):
        levels.append(LevelInfo(
            id=normalize_level_id(item.get("id", "")),
            name=str(item.get("name", "")).strip(),
            file=str(item.get("file", "")).strip(),
            purpose=str(item.get("purpose", item.get("description", ""))).strip(),
            requires_backend=bool(item.get("requires_backend", False)),
            requires_frontend=bool(item.get("requires_frontend", False)),
            requires_playwright=bool(item.get("requires_playwright", False)),
            blocking_for_release=bool(item.get("blocking_for_release", False)),
            raw=item,
        ))
    return sorted(levels, key=lambda lv: lv.id) or scan_levels_folder(root)


def scan_levels_folder(root: Path) -> list[LevelInfo]:
    levels_dir = root / "levels"
    levels = []
    for path in sorted(levels_dir.glob("*.pyw")):
        if path.name.startswith("_"):
            continue
        prefix = path.name.split("-", 1)[0]
        levels.append(LevelInfo(id=normalize_level_id(prefix), name=path.stem, file=f"levels/{path.name}", purpose="Niveau détecté depuis levels/*.pyw."))
    return sorted(levels, key=lambda lv: lv.id)


def find_python_windowed() -> str:
    for candidate in ("pyw", "pythonw"):
        if shutil.which(candidate):
            return candidate
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        maybe = exe.with_name("pythonw.exe")
        if maybe.exists():
            return str(maybe)
    return sys.executable


def find_python_console() -> str:
    for candidate in ("py", "python"):
        if shutil.which(candidate):
            return candidate
    return sys.executable


def level_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    cfg = load_config(root)
    env["LEVELUPDIAG_ROOT"] = str(root)
    env["LEVELUPDIAG_CONFIG"] = str(config_path(root))
    if cfg.get("target_repo_root"):
        env["LEVELUPDIAG_TARGET_REPO_ROOT"] = str(cfg["target_repo_root"])
    if cfg.get("backend_url"):
        env["LEVELUPDIAG_BACKEND_URL"] = str(cfg["backend_url"])
    if cfg.get("frontend_url"):
        env["LEVELUPDIAG_FRONTEND_URL"] = str(cfg["frontend_url"])
    if cfg.get("app_name"):
        env["LEVELUPDIAG_APP_NAME"] = str(cfg["app_name"])
    for key, value in (cfg.get("env") or {}).items():
        env[str(key)] = str(value)
    return env


def launch_level(root: Path, level: LevelInfo, *, console: bool = False, wait: bool = False) -> subprocess.Popen:
    exe = find_python_console() if console else find_python_windowed()
    path = level.file_path(root)
    if not path.exists():
        raise FileNotFoundError(f"Missing level file: {path}")
    proc = subprocess.Popen([exe, str(path)], cwd=str(root), env=level_env(root))
    if wait:
        proc.wait()
    return proc


def open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
