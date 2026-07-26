"""Central configuration for portable LevelUpDiag suites.

Every .pyw level should call load_config() instead of hardcoding local paths,
URLs, commands, tool names, routes or artifact folders.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

CONFIG_ENV = "LEVELUPDIAG_CONFIG"
ROOT_ENV = "LEVELUPDIAG_ROOT"
LOCAL_CONFIG = "levelupdiag.config.local.json"
EXAMPLE_CONFIG = "levelupdiag.config.example.json"
MANIFEST_FILE = "levelupdiag_manifest.json"


def detect_diag_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / MANIFEST_FILE).is_file() and (candidate / "levels").is_dir():
            return candidate
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


@dataclass(slots=True)
class AppConfig:
    diagnostics_repo_root: str
    app_name: str = "My App"
    target_repo_root: str = "."
    backend_url: str = "http://127.0.0.1:8000"
    frontend_url: str = "http://localhost:5173"
    control_dir: str = ".levelupdiag"
    artifacts_dir: str = ".levelupdiag/diagnostics"
    raw: dict[str, Any] = field(default_factory=dict)
    config_path: str = ""

    @property
    def diagnostics_root_path(self) -> Path:
        return Path(self.diagnostics_repo_root)

    @property
    def target_root_path(self) -> Path:
        return Path(self.target_repo_root)

    @property
    def artifacts_root_path(self) -> Path:
        path = self.target_root_path / self.artifacts_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def control_root_path(self) -> Path:
        path = self.target_root_path / self.control_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get(self, dotted: str, default: Any = None) -> Any:
        current: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def path(self, dotted: str, default: str = "") -> Path:
        value = self.get(dotted, default)
        p = Path(str(value))
        return p if p.is_absolute() else self.target_root_path / p

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env[ROOT_ENV] = str(self.diagnostics_root_path)
        if self.config_path:
            env[CONFIG_ENV] = self.config_path
        env["LEVELUPDIAG_TARGET_REPO_ROOT"] = str(self.target_root_path)
        env["LEVELUPDIAG_BACKEND_URL"] = self.backend_url
        env["LEVELUPDIAG_FRONTEND_URL"] = self.frontend_url
        env["LEVELUPDIAG_APP_NAME"] = self.app_name
        for key, value in (self.get("env", {}) or {}).items():
            env[str(key)] = str(value)
        return env

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["raw"] = self.raw
        return data


def config_path(root: Path | None = None) -> Path:
    explicit = os.environ.get(CONFIG_ENV)
    if explicit:
        return Path(explicit)
    diag_root = root or detect_diag_root()
    local = diag_root / LOCAL_CONFIG
    if local.exists():
        return local
    return diag_root / EXAMPLE_CONFIG


def load_config(path: Path | None = None, root: Path | None = None) -> AppConfig:
    diag_root = root or detect_diag_root()
    chosen = path or config_path(diag_root)
    example = diag_root / EXAMPLE_CONFIG
    base: dict[str, Any] = {}
    if example.exists() and chosen != example:
        base = json.loads(example.read_text(encoding="utf-8"))
    if chosen.exists():
        data = json.loads(chosen.read_text(encoding="utf-8"))
    else:
        data = {}
    raw = _deep_merge(base, data)

    # Environment overrides: useful for CI or temporary local runs.
    if os.environ.get("LEVELUPDIAG_TARGET_REPO_ROOT"):
        raw["target_repo_root"] = os.environ["LEVELUPDIAG_TARGET_REPO_ROOT"]
    if os.environ.get("LEVELUPDIAG_BACKEND_URL"):
        raw["backend_url"] = os.environ["LEVELUPDIAG_BACKEND_URL"]
    if os.environ.get("LEVELUPDIAG_FRONTEND_URL"):
        raw["frontend_url"] = os.environ["LEVELUPDIAG_FRONTEND_URL"]
    if os.environ.get("LEVELUPDIAG_APP_NAME"):
        raw["app_name"] = os.environ["LEVELUPDIAG_APP_NAME"]

    return AppConfig(
        diagnostics_repo_root=str(diag_root),
        app_name=str(raw.get("app_name", "My App")),
        target_repo_root=str(raw.get("target_repo_root", ".")),
        backend_url=str(raw.get("backend_url", "http://127.0.0.1:8000")).rstrip("/"),
        frontend_url=str(raw.get("frontend_url", "http://localhost:5173")).rstrip("/"),
        control_dir=str(raw.get("control_dir", ".levelupdiag")),
        artifacts_dir=str(raw.get("artifacts_dir", ".levelupdiag/diagnostics")),
        raw=raw,
        config_path=str(chosen),
    )


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    chosen = path or Path(config.config_path or (config.diagnostics_root_path / LOCAL_CONFIG))
    chosen.parent.mkdir(parents=True, exist_ok=True)
    data = dict(config.raw)
    data.update({
        "app_name": config.app_name,
        "target_repo_root": config.target_repo_root,
        "backend_url": config.backend_url,
        "frontend_url": config.frontend_url,
        "control_dir": config.control_dir,
        "artifacts_dir": config.artifacts_dir,
    })
    chosen.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return chosen
