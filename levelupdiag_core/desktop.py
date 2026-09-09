"""Desktop application services, independent of Tk for automated verification."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
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


class Session:
    def __init__(self, tool):
        self.tool = Path(tool).resolve()
        self.events = queue.SimpleQueue()
        self._lock = threading.Lock()
        self.running = False

    def start(self, campaign, target, database=''):
        cfg = load_config(self.tool, target)
        if campaign not in load_manifest(self.tool)['campaigns']:
            raise ValueError('Unknown campaign.')
        with self._lock:
            if self.running: raise ValueError('A campaign is already running.')
            self.running = True
        env = os.environ.copy()
        if database: env['TEST_DATABASE_URL'] = database
        command = [console_python(), str(self.tool/'levelupdiag.py'), '--target', cfg['_target_root'], 'run', campaign]
        def work():
            try:
                process = subprocess.Popen(command, cwd=str(self.tool), env=env, shell=False,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
                with process.stdout:
                    for line in process.stdout:
                        text = line.replace(database, '<REDACTED>') if database else line
                        self.events.put(('log', redact(text)))
                self.events.put(('done', process.wait()))
            except Exception as error:
                self.events.put(('error', redact(str(error))))
            finally:
                with self._lock: self.running = False
        threading.Thread(target=work, name='orgo-diagnostic', daemon=False).start()
        return cfg
