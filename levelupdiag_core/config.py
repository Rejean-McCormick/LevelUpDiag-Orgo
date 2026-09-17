from __future__ import annotations

import copy
from pathlib import Path
from urllib.parse import quote
from .util import read_dotenv, read_json

DEFAULT_TEST_DATABASE_URL = 'postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test?connection_limit=5'


class ConfigError(RuntimeError):
    pass


def _target_database_environment(target: Path, relative_env_file: str):
    env_path = Path(relative_env_file or '.env')
    if env_path.is_absolute():
        raise ConfigError('database.target_env_file must be relative to the Orgo repository.')
    resolved = (target / env_path).resolve(strict=False)
    if not resolved.is_relative_to(target):
        raise ConfigError('database.target_env_file must stay inside the Orgo repository.')
    values = read_dotenv(resolved, {
        'DATABASE_URL', 'POSTGRES_PASSWORD', 'TEST_DATABASE_URL',
        'ORGO_ADMIN_PASSWORD', 'ORGO_ADMIN_EMAIL', 'ORGO_ORGANIZATION',
        'OIDC_ISSUER', 'OIDC_CLIENT_ID', 'SMTP_URL', 'SMS_GATEWAY_URL', 'WEBHOOK_GATEWAY_URL',
        'KRISTAL_BRIDGE_URL', 'KONNAXION_BRIDGE_URL', 'ARCHITECT_BRIDGE_URL', 'KOA_BRIDGE_URL',
    })
    database_url = values.get('DATABASE_URL', '').strip()
    if not database_url and values.get('POSTGRES_PASSWORD'):
        password = quote(values['POSTGRES_PASSWORD'], safe='')
        database_url = f'postgresql://orgo:{password}@127.0.0.1:5432/orgo'
    return resolved, values, database_url


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

    database = cfg.setdefault('database', {})
    if not isinstance(database, dict):
        raise ConfigError('database configuration must be an object')
    database.setdefault('target_env_file', '.env')
    database.setdefault('test_database_url', DEFAULT_TEST_DATABASE_URL)
    env_path, target_env, database_url = _target_database_environment(target, database['target_env_file'])
    # Runtime-only values stay out of saved configuration and effective reports.
    cfg['_target_env_file'] = str(env_path)
    cfg['_target_env_database_url'] = database_url
    cfg['_target_env_test_database_url'] = target_env.get('TEST_DATABASE_URL', '').strip()
    cfg['_target_env_has_postgres_password'] = bool(target_env.get('POSTGRES_PASSWORD'))
    # Browser credentials are runtime-only. They are deliberately kept under
    # underscore-prefixed keys so they never appear in effective_config.json.
    cfg['_target_env_browser_password'] = target_env.get('ORGO_ADMIN_PASSWORD', '')
    cfg['_target_env_browser_email'] = target_env.get('ORGO_ADMIN_EMAIL', '').strip()
    cfg['_target_env_browser_organization'] = target_env.get('ORGO_ORGANIZATION', '').strip()
    provider_map = {
        'oidc': ('OIDC_ISSUER', 'OIDC_CLIENT_ID'),
        'smtp': ('SMTP_URL',),
        'sms': ('SMS_GATEWAY_URL',),
        'webhook': ('WEBHOOK_GATEWAY_URL',),
        'kristal': ('KRISTAL_BRIDGE_URL',),
        'konnaxion': ('KONNAXION_BRIDGE_URL',),
        'architect': ('ARCHITECT_BRIDGE_URL',),
        'koa': ('KOA_BRIDGE_URL',),
    }
    cfg['_target_env_configured_providers'] = [
        name for name, keys in provider_map.items() if all(target_env.get(key, '').strip() for key in keys)
    ]
    return cfg
