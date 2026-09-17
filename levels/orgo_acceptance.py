"""High-confidence local acceptance on disposable resources only.

N14 deliberately automates what can be proven without touching production data or
sending provider operations to external systems: shipped backup/restore scripts,
an isolated production Docker Compose deployment, and the full Playwright suite.
External provider endpoints are inventoried but never invoked implicitly.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import ProxyHandler, build_opener

from levelupdiag_core.commands import run_command
from levelupdiag_core.test_runtime import TestRuntime, api_is_ready, occupied
from levelupdiag_core.util import redact
from levels import orgo_browser

MANAGED_CONTAINER = 'orgo-test-postgres'
MANAGED_DATABASE = 'orgo_test'
MANAGED_USER = 'orgo_test'
EXTERNAL_ENV_KEYS = (
    'OIDC_ISSUER', 'OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET',
    'SMS_GATEWAY_URL', 'SMS_GATEWAY_TOKEN',
    'WEBHOOK_GATEWAY_URL', 'WEBHOOK_GATEWAY_TOKEN',
    'SMTP_URL', 'SMTP_FROM',
    'KRISTAL_BRIDGE_URL', 'KRISTAL_BRIDGE_TOKEN',
    'KONNAXION_BRIDGE_URL', 'KONNAXION_BRIDGE_TOKEN',
    'ARCHITECT_BRIDGE_URL', 'ARCHITECT_BRIDGE_TOKEN',
    'KOA_BRIDGE_URL', 'KOA_BRIDGE_TOKEN',
)


def managed_test_database(value: str) -> bool:
    """True only for the fixed localhost database owned by TestRuntime."""
    try:
        url = urlsplit(value or '')
        database = unquote(url.path.lstrip('/'))
        return (
            url.scheme in ('postgres', 'postgresql')
            and url.hostname in ('127.0.0.1', 'localhost', '::1')
            and (url.port or 5432) == 5432
            and unquote(url.username or '') == MANAGED_USER
            and database == MANAGED_DATABASE
        )
    except ValueError:
        return False


def _safe_suffix(run_id: str) -> str:
    value = re.sub(r'[^a-z0-9]', '', run_id.lower())[-12:]
    return value or secrets.token_hex(6)


def _query_count(runtime: TestRuntime, database: str, sql: str) -> int:
    output = runtime.docker(
        'exec', MANAGED_CONTAINER, 'psql', '-U', MANAGED_USER, '-d', database,
        '-At', '-v', 'ON_ERROR_STOP=1', '-c', sql,
    ).strip()
    return int(output.splitlines()[-1])


def backup_restore_acceptance(cfg, report):
    """Exercise Orgo's shipped backup/restore scripts on the managed test DB."""
    target = Path(cfg['_target_root'])
    test_url = os.environ.get('TEST_DATABASE_URL', '')
    if not managed_test_database(test_url):
        report.add(
            'orgo.acceptance.backup_restore', 'BLOCKED', 'acceptance',
            'Automatic backup/restore is confined to the validated localhost orgo_test container.',
            recommendation='Use Reset / Prepare PostgreSQL test before acceptance; custom databases require explicit operator-managed restore evidence.',
        )
        return False
    backup = target / 'scripts' / 'operations' / 'backup.sh'
    restore = target / 'scripts' / 'operations' / 'restore.sh'
    if not backup.is_file() or not restore.is_file():
        report.add('orgo.acceptance.backup_restore', 'FAIL', 'acceptance',
                   'The shipped backup/restore scripts are missing.')
        return False
    if not shutil.which('docker'):
        report.add('orgo.acceptance.backup_restore', 'BLOCKED', 'tooling',
                   'Docker is required for isolated backup/restore acceptance.')
        return False

    runtime = TestRuntime(cfg['_tool_root'])
    suffix = _safe_suffix(report.run_id)
    restore_db = f'orgo_restore_validation_{suffix}'
    dump = f'/tmp/orgo-acceptance-{suffix}.dump'
    backup_remote = f'/tmp/orgo-backup-{suffix}.sh'
    restore_remote = f'/tmp/orgo-restore-{suffix}.sh'
    internal_source = 'postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test'
    internal_restore = f'postgresql://orgo_test:orgo_test@127.0.0.1:5432/{restore_db}'
    cleanup_errors = []
    stage = 'validate-managed-database'
    try:
        runtime.ensure_database()  # validates container identity before any destructive command
        stage = 'copy-backup-script'
        runtime.docker('cp', str(backup), f'{MANAGED_CONTAINER}:{backup_remote}')
        stage = 'copy-restore-script'
        runtime.docker('cp', str(restore), f'{MANAGED_CONTAINER}:{restore_remote}')
        stage = 'drop-temporary-restore-database'
        runtime.docker('exec', MANAGED_CONTAINER, 'dropdb', '-U', MANAGED_USER, '--if-exists', restore_db)
        stage = 'create-temporary-restore-database'
        runtime.docker('exec', MANAGED_CONTAINER, 'createdb', '-U', MANAGED_USER, '-T', 'template0', restore_db)
        stage = 'run-shipped-backup-script'
        runtime.docker('exec', '-e', f'DATABASE_URL={internal_source}', MANAGED_CONTAINER,
                       'bash', backup_remote, dump)
        stage = 'run-shipped-restore-script'
        runtime.docker('exec', '-e', f'RESTORE_DATABASE_URL={internal_restore}', MANAGED_CONTAINER,
                       'bash', restore_remote, '--restore-to-empty-database', dump)
        table_sql = "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
        migration_sql = 'SELECT count(*) FROM "_prisma_migrations" WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL;'
        stage = 'compare-source-table-count'
        source_tables = _query_count(runtime, MANAGED_DATABASE, table_sql)
        stage = 'compare-restored-table-count'
        restored_tables = _query_count(runtime, restore_db, table_sql)
        stage = 'compare-source-migration-count'
        source_migrations = _query_count(runtime, MANAGED_DATABASE, migration_sql)
        stage = 'compare-restored-migration-count'
        restored_migrations = _query_count(runtime, restore_db, migration_sql)
        ok = (source_tables > 0 and source_tables == restored_tables and
              source_migrations > 0 and source_migrations == restored_migrations)
        report.metrics['backup_restore'] = {
            'source_tables': source_tables,
            'restored_tables': restored_tables,
            'source_migrations': source_migrations,
            'restored_migrations': restored_migrations,
        }
        report.add(
            'orgo.acceptance.backup_restore', 'PASS' if ok else 'FAIL', 'acceptance',
            'Shipped backup.sh and restore.sh completed against an isolated restore database.' if ok
            else 'Backup/restore completed but restored schema evidence did not match the source test database.',
            evidence=report.metrics['backup_restore'],
        )
        return ok
    except Exception as error:
        report.add(
            'orgo.acceptance.backup_restore', 'FAIL', 'acceptance',
            'Automated backup/restore acceptance failed.',
            evidence={'stage': stage, 'error': redact(str(error))},
            recommendation='Inspect the reported stage/error; LevelUpDiag keeps credentials redacted.',
        )
        return False
    finally:
        for args in (
            ('exec', MANAGED_CONTAINER, 'dropdb', '-U', MANAGED_USER, '--if-exists', restore_db),
            ('exec', MANAGED_CONTAINER, 'rm', '-f', dump, backup_remote, restore_remote),
        ):
            try:
                runtime.docker(*args)
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        if cleanup_errors:
            report.add('orgo.acceptance.backup_restore.cleanup', 'INFRA_ERROR', 'cleanup',
                       'Could not fully clean temporary backup/restore resources.',
                       evidence={'errors': cleanup_errors})


def _http_ready(url: str, seconds: int, api: bool = False) -> bool:
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=3) as response:
                if response.status != 200:
                    time.sleep(1)
                    continue
                if not api:
                    return True
                return api_is_ready(json.loads(response.read()))
        except (OSError, ValueError, json.JSONDecodeError):
            time.sleep(1)
    return False


def _compose_env(report) -> dict:
    env = os.environ.copy()
    # Prevent the ephemeral deployment from inheriting live external-provider endpoints.
    for key in EXTERNAL_ENV_KEYS:
        env[key] = ''
    suffix = _safe_suffix(report.run_id)
    env.update({
        'POSTGRES_PASSWORD': f'orgo_acceptance_{suffix}',
        'ORGO_PUBLIC_URL': 'http://127.0.0.1:3000',
        'ORGO_ADMIN_PASSWORD': os.environ.get('ORGO_E2E_PASSWORD', ''),
        'ORGO_ADMIN_EMAIL': os.environ.get('ORGO_E2E_EMAIL', ''),
        'ORGO_ORGANIZATION': os.environ.get('ORGO_E2E_ORGANIZATION', ''),
    })
    return env


def deployment_and_browser_acceptance(cfg, report):
    """Build/start the real production Compose stack, seed it, then run Playwright."""
    target = Path(cfg['_target_root'])
    compose_file = target / 'docker-compose.yml'
    if not compose_file.is_file():
        report.add('orgo.acceptance.deployment', 'FAIL', 'deployment', 'docker-compose.yml is missing.')
        return False
    if not shutil.which('docker'):
        report.add('orgo.acceptance.deployment', 'BLOCKED', 'tooling', 'Docker is required for deployment acceptance.')
        return False
    if occupied(3000) or occupied(4000):
        report.add('orgo.acceptance.deployment', 'BLOCKED', 'deployment',
                   'Ports 3000 or 4000 are occupied. Acceptance will not replace an existing local service.',
                   recommendation='Stop Orgo test/manual local services, then rerun acceptance.')
        return False
    required = ('ORGO_E2E_ORGANIZATION', 'ORGO_E2E_EMAIL', 'ORGO_E2E_PASSWORD')
    missing = [key for key in required if not os.environ.get(key)]
    if missing or os.environ.get('ORGO_E2E_ALLOW_WRITES') != 'test-instance':
        report.add('orgo.acceptance.deployment', 'BLOCKED', 'configuration',
                   'Acceptance needs the disposable browser account and explicit write consent.',
                   evidence={'missing_variables': missing})
        return False

    project = 'ludaccept' + _safe_suffix(report.run_id)
    env = _compose_env(report)
    base = ['docker', 'compose', '-p', project]
    artifact_dir = Path(cfg['_control_root']) / 'runs' / report.run_id / 'acceptance'
    artifact_dir.mkdir(parents=True, exist_ok=True)
    started = False
    ok = False
    try:
        version = run_command(['docker', 'compose', 'version'], cwd=target, timeout_seconds=30,
                              capture_limit_kb=64, env=env)
        if version['timed_out'] or version['exit_code'] != 0:
            report.add('orgo.acceptance.deployment', 'BLOCKED', 'tooling',
                       'Docker Compose v2 is not available.', evidence=version)
            return False
        up = run_command(base + ['up', '-d', '--build', 'postgres', 'migrate', 'api', 'worker', 'web'],
                         cwd=target, timeout_seconds=2400, capture_limit_kb=512, env=env)
        started = True
        if up['timed_out'] or up['exit_code'] != 0:
            report.add('orgo.acceptance.deployment', 'INFRA_ERROR' if up['timed_out'] else 'FAIL', 'deployment',
                       'The isolated production Compose stack did not start successfully.', evidence=up)
            return False
        if not _http_ready('http://127.0.0.1:4000/health/ready', 180, api=True):
            report.add('orgo.acceptance.deployment', 'FAIL', 'deployment',
                       'Production API did not become ready on the isolated Compose stack.')
            return False
        if not _http_ready('http://127.0.0.1:3000/', 180):
            report.add('orgo.acceptance.deployment', 'FAIL', 'deployment',
                       'Production web did not become ready on the isolated Compose stack.')
            return False
        seed = run_command(base + ['--profile', 'setup', 'run', '--rm', 'seed'],
                           cwd=target, timeout_seconds=600, capture_limit_kb=256, env=env)
        if seed['timed_out'] or seed['exit_code'] != 0:
            report.add('orgo.acceptance.deployment', 'INFRA_ERROR' if seed['timed_out'] else 'FAIL', 'deployment',
                       'The isolated production deployment started, but test-account seeding failed.', evidence=seed)
            return False
        services = run_command(base + ['ps', '--status', 'running', '--services'], cwd=target,
                               timeout_seconds=60, capture_limit_kb=64, env=env)
        running = set(services.get('stdout_tail', '').split())
        expected = {'postgres', 'api', 'worker', 'web'}
        if services['exit_code'] != 0 or not expected.issubset(running):
            report.add('orgo.acceptance.deployment', 'FAIL', 'deployment',
                       'Not all long-running production services stayed up after readiness.',
                       evidence={'running_services': sorted(running), 'expected_services': sorted(expected)})
            return False
        report.metrics['deployment_services'] = sorted(running)
        report.add('orgo.acceptance.deployment', 'PASS', 'deployment',
                   'Docker Compose built and started an isolated production API/web/worker/PostgreSQL stack; health and seed completed.',
                   evidence={'services': sorted(running), 'project': project})

        previous_url = os.environ.get('ORGO_E2E_URL')
        os.environ['ORGO_E2E_URL'] = 'http://127.0.0.1:3000'
        try:
            before = len(report.findings)
            orgo_browser.run(cfg, report)
            browser_findings = report.findings[before:]
            ok = bool(browser_findings) and all(item.get('verdict') == 'PASS' for item in browser_findings)
        finally:
            if previous_url is None:
                os.environ.pop('ORGO_E2E_URL', None)
            else:
                os.environ['ORGO_E2E_URL'] = previous_url
        return ok
    except OSError as error:
        report.add('orgo.acceptance.deployment', 'BLOCKED', 'tooling',
                   'Docker Compose could not be launched.', evidence=type(error).__name__)
        return False
    finally:
        if started:
            try:
                logs = run_command(base + ['logs', '--no-color', '--tail', '250', 'migrate', 'api', 'worker', 'web'],
                                   cwd=target, timeout_seconds=90, capture_limit_kb=512, env=env)
                log_path = artifact_dir / 'compose.log'
                log_path.write_text((logs.get('stdout_tail', '') + '\n' + logs.get('stderr_tail', '')).strip() + '\n', encoding='utf-8')
                report.artifact('compose-logs', log_path, 'Redacted tail of isolated production deployment logs.')
            except Exception:
                pass
            try:
                down = run_command(base + ['down', '-v', '--remove-orphans'], cwd=target,
                                   timeout_seconds=900, capture_limit_kb=256, env=env)
                cleanup_ok = down['exit_code'] == 0 and not down['timed_out']
                report.add('orgo.acceptance.deployment.cleanup', 'PASS' if cleanup_ok else 'INFRA_ERROR', 'cleanup',
                           'Isolated production Compose project and volume were removed.' if cleanup_ok
                           else 'Could not fully remove the isolated production Compose project.', evidence=down)
            except Exception as error:
                report.add('orgo.acceptance.deployment.cleanup', 'INFRA_ERROR', 'cleanup',
                           'Could not fully remove the isolated production Compose project.', evidence=type(error).__name__)


def provider_boundary(cfg, report):
    configured = list(cfg.get('_target_env_configured_providers', []) or [])
    if configured:
        report.add('orgo.acceptance.external_providers', 'WARN', 'external-provider',
                   'External provider configuration was detected but LevelUpDiag did not send live provider operations automatically.',
                   evidence={'configured_provider_classes': configured},
                   recommendation='Retain provider-specific live acceptance separately when those integrations are in production scope.')
    else:
        report.add('orgo.acceptance.external_providers', 'PASS', 'external-provider',
                   'No external provider endpoint is configured in the target .env; live provider acceptance is not part of this local deployment scope.')


def run(cfg, report):
    execution = cfg.get('execution', {})
    if not execution.get('allow_target_mutation', False) or not execution.get('allow_network', False):
        report.add('orgo.acceptance.policy', 'BLOCKED', 'policy',
                   'Automated acceptance requires both target mutation and network permissions for Docker builds, PostgreSQL and browser execution.')
        return
    if not backup_restore_acceptance(cfg, report):
        return
    if not deployment_and_browser_acceptance(cfg, report):
        return
    provider_boundary(cfg, report)
