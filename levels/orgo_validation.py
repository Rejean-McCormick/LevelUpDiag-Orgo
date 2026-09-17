"""Orgo-specific levels reuse public validators; no production DB inference."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
from levelupdiag_core.commands import run_command

STEPS = {
    'N08': [('generate', True, False), ('architecture', False, False), ('types', True, False)],
    'N09': [('launcher', False, False), ('unit', True, False)],
    'N10': [('pglite', True, False)],
    'N11': [('migrate', True, True), ('integration', True, True)],
    'N12': [('build', True, False)],
    'N13': [('audit', False, True)],
}

def test_database_valid(value):
    try:
        u = urlsplit(value or '')
        return bool(u.scheme in ('postgres', 'postgresql') and u.hostname and
                    re.search(r'(^|[_-])(test|validation)([_-]|$)', unquote(u.path[1:]), re.I))
    except ValueError:
        return False

def run(cfg, report):
    target = Path(cfg['_target_root'])
    if report.level_id == 'N07':
        required = ['package.json', 'package-lock.json', 'apps/api/prisma/schema.prisma',
                    'apps/api/test/integration/runtime.test.ts']
        missing = [p for p in required if not (target / p).is_file()]
        report.add('orgo.layout', 'BLOCKED' if missing else 'PASS', 'context',
                   'Orgo diagnostic entrypoints and source layout.', evidence={'missing': missing})
        if missing: return
        package = json.loads((target / 'package.json').read_text(encoding='utf-8'))
        needed = ['db:generate', 'db:migrate', 'check:architecture', 'typecheck', 'test', 'test:integration', 'test:pglite', 'build']
        absent = [name for name in needed if name not in package.get('scripts', {})]
        report.add('orgo.scripts', 'BLOCKED' if absent else 'PASS', 'context', 'Public validators declared.', evidence={'missing': absent})
        try:
            result = run_command(['node', '--version'], cwd=target, timeout_seconds=15)
            version = int(result['stdout_tail'].strip().lstrip('v').split('.')[0])
            ok = result['exit_code'] == 0 and version >= 22
            report.add('orgo.node', 'PASS' if ok else 'BLOCKED', 'tooling', 'Node.js 22+ required.', evidence=result)
        except (OSError, ValueError):
            report.add('orgo.node', 'BLOCKED', 'tooling', 'Node.js 22+ could not be identified.')
        installed = (target / 'node_modules').is_dir()
        report.add('orgo.dependencies', 'PASS' if installed else 'BLOCKED', 'tooling',
                   'Dependency directory present; command execution will verify usability.' if installed else 'Run npm ci explicitly before validation.')
        return
    execution = cfg.get('execution', {})
    for step, mutates, network in STEPS[report.level_id]:
        if mutates and not execution.get('allow_target_mutation', False):
            report.add('orgo.'+step, 'BLOCKED', 'policy', 'Enable allow_target_mutation locally to execute '+step+'.')
            break
        if network and not execution.get('allow_network', False):
            report.add('orgo.'+step, 'BLOCKED', 'policy', 'Enable allow_network locally to execute '+step+'.')
            break
        if step in ('migrate', 'integration') and not test_database_valid(os.environ.get('TEST_DATABASE_URL')):
            report.add('orgo.'+step, 'BLOCKED', 'database', 'TEST_DATABASE_URL must identify a dedicated PostgreSQL test/validation database; DATABASE_URL is never used as a fallback.')
            break
        try:
            result = run_command(['node', str(Path(cfg['_tool_root'])/'adapters/diag-step.mjs'), step, str(target.resolve())], cwd=target,
                                 timeout_seconds=1200, capture_limit_kb=execution.get('capture_limit_kb', 256),
                                 redact_output=True)
            verdict = 'INFRA_ERROR' if result['timed_out'] else ('PASS' if result['exit_code'] == 0 else ('BLOCKED' if result['exit_code'] == 20 else 'FAIL'))
        except OSError as error:
            report.add('orgo.'+step, 'BLOCKED', 'tooling', 'Command could not start.', evidence=type(error).__name__)
            break
        if step in ('launcher', 'unit', 'pglite', 'integration') and verdict == 'PASS':
            counts = {}
            for key in ('tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo'):
                match = re.search(r'(?:^|\n)[#ℹ] '+key+r' (\d+)', result.get('stdout_tail', ''))
                if match: counts[key] = int(match.group(1))
            report.metrics[step+'_counts'] = counts
            if not counts.get('tests'):
                verdict = 'PARTIAL'
            elif counts.get('fail', 0) or counts.get('cancelled', 0):
                verdict = 'FAIL'
            elif step != 'pglite' and (counts.get('skipped', 0) or counts.get('todo', 0)):
                verdict = 'PARTIAL'
        report.add('orgo.'+step, verdict, 'validation', 'Public Orgo validator: '+step, evidence=result)
        if step == 'pglite' and verdict == 'PASS':
            report.add('orgo.pglite.limit', 'WARN', 'coverage', 'PGlite is not native PostgreSQL: multi-connection lock acceptance is deliberately skipped. Run N11 for native coverage.')
        if verdict != 'PASS': break
