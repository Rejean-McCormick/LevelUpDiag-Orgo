"""Own only the API/web processes started by this console; never delete data."""
import json
import os
import queue
import shutil
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.request import build_opener, ProxyHandler

TEST_DATABASE = 'postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test?connection_limit=5'


def api_is_ready(payload):
    if not isinstance(payload, dict):
        return False
    if 'ok' in payload:
        return (payload['ok'] is True and isinstance(payload.get('data'), dict)
                and payload['data'].get('status') == 'ready')
    return payload.get('status') == 'ready'


def occupied(port):
    for host in ('127.0.0.1', '::1'):
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            pass
    return False


def cli_path(target, workspace, package, relative):
    for base in (target / 'apps' / workspace, target):
        candidate = base / 'node_modules' / package / relative
        if candidate.is_file():
            return candidate
    raise ValueError(f'Missing {package}. Run npm ci in the Orgo repository first.')


class TestRuntime:
    def __init__(self, tool):
        self.tool = Path(tool)
        self.events = queue.SimpleQueue()
        self.processes = []
        self.logs = []
        self.busy = False
        self.ready = False
        self.cancel = threading.Event()
        self.log_dir = None

    def docker(self, *args):
        result = subprocess.run(['docker', *args], capture_output=True, text=True,
                                timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('Docker command failed. Open Docker Desktop and verify the existing orgo-test-postgres container.')
        return result.stdout

    def ensure_database(self):
        self.events.put(('status', 'Starting PostgreSQL test container…'))
        info = json.loads(self.docker('inspect', 'orgo-test-postgres'))[0]
        container_env = dict(value.split('=', 1) for value in info['Config'].get('Env', []) if '=' in value)
        for key, value in [('POSTGRES_DB', 'orgo_test'), ('POSTGRES_USER', 'orgo_test'), ('POSTGRES_PASSWORD', 'orgo_test')]:
            if container_env.get(key) != value:
                raise RuntimeError('The existing test container configuration differs from the documented orgo_test setup.')
        bindings = info['HostConfig'].get('PortBindings', {}).get('5432/tcp') or []
        if not any(item.get('HostPort') == '5432' and item.get('HostIp') in ('', '0.0.0.0', '127.0.0.1') for item in bindings):
            raise RuntimeError('Test PostgreSQL must publish port 5432 on localhost.')
        self.docker('start', 'orgo-test-postgres')
        deadline = time.monotonic() + 45
        while True:
            if self.cancel.is_set():
                raise RuntimeError('Startup cancelled.')
            try:
                self.docker('exec', 'orgo-test-postgres', 'pg_isready', '-U', 'orgo_test', '-d', 'orgo_test')
                return TEST_DATABASE
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('PostgreSQL did not become ready.')
                self.cancel.wait(1)

    def prepare_database(self):
        if self.busy or self.processes:
            raise ValueError('Stop the running Orgo test runtime before preparing PostgreSQL.')
        if not shutil.which('docker'):
            raise ValueError('Docker must be installed and available in PATH.')
        self.busy = True
        self.cancel.clear()

        def work():
            try:
                url = self.ensure_database()
                self.events.put(('database-ready', url))
            except Exception as error:
                self.events.put(('error', str(error)))
            finally:
                self.busy = False
                self.events.put(('idle', ''))

        threading.Thread(target=work, daemon=False).start()

    def launch(self, command, cwd, env, name):
        log = (self.log_dir / (name + '.log')).open('wb')
        self.logs.append(log)
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name != 'nt',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
        self.processes.append(process)
        return process

    def wait_ready(self, url, process, seconds, api=False):
        deadline = time.monotonic() + seconds
        opener = build_opener(ProxyHandler({}))
        while time.monotonic() < deadline:
            if self.cancel.is_set(): raise RuntimeError('Startup cancelled.')
            if process.poll() is not None: raise RuntimeError('Orgo exited during startup. Inspect runtime logs.')
            try:
                with opener.open(url, timeout=2) as response:
                    if response.status == 200:
                        if not api or api_is_ready(json.loads(response.read())):
                            return
            except (OSError, ValueError):
                pass
            self.cancel.wait(0.5)
        raise RuntimeError(f'Startup timed out at {url}. Inspect runtime logs.')

    def start(self, target):
        if self.busy or self.processes: raise ValueError('Test runtime is already starting or running.')
        target = Path(target).resolve()
        if not shutil.which('node') or not shutil.which('docker'):
            raise ValueError('Node.js and Docker must be installed and available in PATH.')
        tsx = cli_path(target, 'api', 'tsx', 'dist/cli.mjs')
        next_cli = cli_path(target, 'web', 'next', 'dist/bin/next')
        if not (target / 'apps/api/src/main.ts').is_file():
            raise ValueError('Select the Orgo repository root.')
        if occupied(4000) or occupied(3000):
            raise ValueError('Port 3000 or 4000 is already occupied. Close your manually started Orgo windows before using automatic startup.')
        self.log_dir = self.tool / 'runtime-logs' / str(time.time_ns())
        self.log_dir.mkdir(parents=True)
        self.busy = True
        self.cancel.clear()
        def work():
            try:
                database_url = self.ensure_database()
                self.events.put(('database-ready', database_url))
                env = os.environ.copy()
                for key in list(env):
                    if (key.startswith('ORGO_E2E_') or key.startswith('OIDC_')
                            or key in ('ORGO_ADMIN_PASSWORD', 'ORGO_PUBLIC_URL')):
                        env.pop(key)
                env.update(DATABASE_URL=TEST_DATABASE, PORT='4000', NODE_ENV='development')
                self.events.put(('status', 'Starting Orgo API on port 4000…'))
                api = self.launch([shutil.which('node'), str(tsx), 'src/main.ts'], target / 'apps/api', env, 'api')
                self.wait_ready('http://127.0.0.1:4000/health/ready', api, 90, api=True)
                env.update(ORGO_API_URL='http://127.0.0.1:4000', PORT='3000')
                self.events.put(('status', 'Starting Orgo frontend on port 3000…'))
                web = self.launch([shutil.which('node'), str(next_cli), 'dev', '-H', '127.0.0.1', '-p', '3000'], target / 'apps/web', env, 'web')
                self.wait_ready('http://127.0.0.1:3000', web, 120)
                if api.poll() is not None: raise RuntimeError('API exited while frontend was starting.')
                self.ready = True
                self.events.put(('ready', 'Orgo test is ready at http://127.0.0.1:3000. You can run browser.'))
            except Exception as error:
                try: self.cleanup()
                except Exception as cleanup_error:
                    self.events.put(('error', str(cleanup_error)))
                self.events.put(('error', str(error)))
            finally:
                self.busy = False
                self.events.put(('idle', ''))
        threading.Thread(target=work, daemon=False).start()

    def cleanup(self):
        remaining = []
        for process in reversed(self.processes):
            if process.poll() is not None: continue
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               capture_output=True, timeout=15,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            else:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                remaining.append(process)
        self.processes = remaining
        self.ready = False
        if remaining: raise RuntimeError('An owned process could not be stopped. Inspect runtime logs and close it manually.')
        for log in self.logs: log.close()
        self.logs.clear()

    def stop(self):
        if self.busy:
            self.cancel.set()
            return
        self.busy = True
        def work():
            try:
                self.cleanup()
                self.events.put(('status', 'Orgo API/frontend stopped. PostgreSQL and its data are preserved.'))
            except Exception as error: self.events.put(('error', str(error)))
            finally:
                self.busy = False
                self.events.put(('idle', ''))
        threading.Thread(target=work, daemon=False).start()
