from __future__ import annotations

import copy
from pathlib import Path
from .util import read_json

class ConfigError(RuntimeError):
    pass


def _merge(base, overlay):
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(tool_root: Path, target_override=None):
    base_path = tool_root / "levelupdiag.config.json"
    if not base_path.exists():
        raise ConfigError(f"Missing configuration: {base_path}")
    cfg = read_json(base_path)
    local = tool_root / "levelupdiag.config.local.json"
    if local.exists():
        cfg = _merge(cfg, read_json(local))
    if cfg.get("schema") != "levelupdiag.config.v2":
        raise ConfigError("Unsupported config schema")

    target_value = target_override or cfg.get("target_repo_root", "auto")
    if str(target_value).lower() == "auto":
        raise ConfigError('Specify the separate Orgo repository with --target or target_repo_root in local configuration.')
    else:
        p = Path(target_value).expanduser()
        target = p if p.is_absolute() else ((Path.cwd() if target_override else tool_root) / p)
    target = target.resolve(strict=False)
    if not target.exists() or not target.is_dir():
        raise ConfigError(f"Target repository root is not a directory: {target}")
    cfg["_tool_root"] = str(tool_root.resolve())
    cfg["_target_root"] = str(target)
    tool = tool_root.resolve()
    if tool.is_relative_to(target) or target.is_relative_to(tool):
        raise ConfigError('LevelUpDiag-Orgo and Orgo must be separate, non-nested directories.')
    control = Path(cfg.get("control_dir", ".levelupdiag"))
    if control.is_absolute():
        raise ConfigError("control_dir must be relative to the diagnostic application")
    cfg["_control_root"] = str((tool / control).resolve(strict=False))
    if not Path(cfg["_control_root"]).is_relative_to(tool) or Path(cfg["_control_root"]) == tool:
        raise ConfigError("control_dir must stay in a subdirectory of the diagnostic application")
    return cfg
