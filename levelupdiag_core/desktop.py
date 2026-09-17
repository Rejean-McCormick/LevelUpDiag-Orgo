"""Desktop application services, independent of Tk for automated verification."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit
from .config import load_config
from .manifest import load_manifest
from .util import read_json, write_json, redact


def save_settings(tool, target, mutation, network):
    # Validate before touching the user's existing local configuration.
    cfg = load_config(tool, target)
    if not (Path(cfg['_target_root'])/'package.json').is_file():
        raise ValueError('Select the Orgo root containing package.json.')
    local = tool/'levelupdiag.config.local.json'
    data = read_json(local) if local.exists() else {}
    data['target_repo_root'] = cfg['_target_root']
    execution = data.setdefault('execution', {})
    execution.update(allow_target_mutation=bool(mutation), allow_network=bool(network))
    write_json(local, data)
    return load_config(tool)


def console_python():
    exe = Path(sys.executable)
    console = exe.with_name('python.exe')
    return str(console if exe.name.lower() == 'pythonw.exe' and console.exists() else exe)


def report_path(control, run_id, relative='summary.json'):
    runs = (Path(control)/'runs').resolve()
    directory = (runs/run_id).resolve()
    if directory.parent != runs:
        raise ValueError('Invalid report ID.')
    result = (directory/relative).resolve()
    if not result.is_relative_to(directory):
        raise ValueError('Invalid report path.')
    return result


def history(control, limit=40):
    runs = Path(control)/'runs'
    if not runs.is_dir(): return []
    results = []
    for directory in sorted(runs.iterdir(), reverse=True):
        if not directory.is_dir() or directory.is_symlink(): continue
        try:
            summary = read_json(report_path(control, directory.name))
            if summary.get('run_id') != directory.name: continue
            results.append(summary)
        except (OSError, ValueError): continue
        if len(results) >= limit: break
    return results



def browser_defaults_from_config(cfg):
    """Resolve browser account defaults from Orgo's target .env in memory only."""
    return {
        'organization': str(cfg.get('_target_env_browser_organization', '') or 'orgo-e2e').strip(),
        'email': str(cfg.get('_target_env_browser_email', '') or 'e2e@example.test').strip(),
        'password': str(cfg.get('_target_env_browser_password', '') or ''),
    }

def browser_environment(settings):
    url = settings.get('url', '').strip()
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')
                 and not parsed.username and not parsed.password and not parsed.query
                 and not parsed.fragment and parsed.path in ('', '/'))
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Browser URL must be a local HTTP origin, for example http://127.0.0.1:3000.')
    if not all(settings.get(key, '').strip() for key in ('organization', 'email', 'password')):
        raise ValueError('Enter the test organization, email and password in the Browser settings tab.')
    if not settings.get('allow_writes'):
        raise ValueError('Confirm that browser writes target a disposable test instance.')
    return {
        'ORGO_E2E_URL': url,
        'ORGO_E2E_ORGANIZATION': settings['organization'].strip(),
        'ORGO_E2E_EMAIL': settings['email'].strip(),
        'ORGO_E2E_PASSWORD': settings['password'],
        'ORGO_E2E_ALLOW_WRITES': 'test-instance',
    }


class Session:
    def __init__(self, tool):
        self.tool = Path(tool).resolve()
        self.events = queue.SimpleQueue()
        self._lock = threading.Lock()
        self.running = False

    def start(self, campaign, target, database='', browser=None):
        cfg = load_config(self.tool, target)
        if campaign not in load_manifest(self.tool)['campaigns']:
            raise ValueError('Unknown campaign.')
        browser_env = browser_environment(browser or {}) if campaign in {'browser', 'acceptance'} else {}
        configured_database = str(cfg.get('database', {}).get('test_database_url', '') or '').strip()
        target_env_database = str(cfg.get('_target_env_test_database_url', '') or '').strip()
        resolved_database = (database or os.environ.get('TEST_DATABASE_URL') or
                             configured_database or target_env_database).strip()
        if campaign in {'database', 'deep', 'acceptance'} and not resolved_database:
            raise ValueError('Configure, prepare or enter a dedicated TEST_DATABASE_URL before running a native PostgreSQL campaign.')
        with self._lock:
            if self.running: raise ValueError('A campaign is already running.')
            self.running = True
        env = os.environ.copy()
        # Do not leak browser credentials into other campaigns through inheritance.
        for key in list(env):
            if key.startswith('ORGO_E2E_'): del env[key]
        env.update(browser_env)
        if campaign in {'database', 'deep', 'acceptance'} and resolved_database:
            env['TEST_DATABASE_URL'] = resolved_database
        secrets = [value for value in (resolved_database, browser_env.get('ORGO_E2E_PASSWORD')) if value]
        def sanitized(value):
            for secret in secrets: value = value.replace(secret, '<REDACTED>')
            return redact(value)
        command = [console_python(), str(self.tool/'levelupdiag.py'), '--target', cfg['_target_root'], 'run', campaign]
        def work():
            try:
                process = subprocess.Popen(command, cwd=str(self.tool), env=env, shell=False,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
                with process.stdout:
                    for line in process.stdout:
                        self.events.put(('log', sanitized(line)))
                self.events.put(('done', process.wait()))
            except Exception as error:
                self.events.put(('error', sanitized(str(error))))
            finally:
                with self._lock: self.running = False
        threading.Thread(target=work, name='orgo-diagnostic', daemon=False).start()
        return cfg
