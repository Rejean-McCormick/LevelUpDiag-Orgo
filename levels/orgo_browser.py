"""Real browser acceptance against an explicitly selected local test instance."""
import json
import os
from pathlib import Path
from levelupdiag_core.commands import run_command


def run(cfg, report):
    execution = cfg.get('execution', {})
    required = ['ORGO_E2E_ORGANIZATION', 'ORGO_E2E_EMAIL', 'ORGO_E2E_PASSWORD']
    missing = [key for key in required if not os.environ.get(key)]
    browser = Path(cfg['_tool_root']) / 'browser'
    cli = browser / 'node_modules' / '@playwright' / 'test' / 'cli.js'
    if (missing or not cli.is_file() or
            os.environ.get('ORGO_E2E_ALLOW_WRITES') != 'test-instance' or
            not execution.get('allow_target_mutation') or not execution.get('allow_network')):
        report.add('orgo.browser.preflight', 'BLOCKED', 'configuration',
                   'Install browser dependencies, configure E2E credentials and explicitly allow test-instance writes and network access.',
                   evidence={'missing_variables': missing, 'playwright_installed': cli.is_file()},
                   recommendation='Follow PLAYWRIGHT_ORGO.md in the diagnostic repository.')
        return
    output = browser / 'runs' / report.run_id
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ORGO_E2E_JSON=str(output / 'results.json'),
               ORGO_E2E_HTML=str(output / 'html'), ORGO_E2E_RESULTS=str(output / 'artifacts'))
    result = run_command(['node', str(cli), 'test'], cwd=browser, timeout_seconds=900, env=env)
    verdict = 'INFRA_ERROR' if result['timed_out'] else 'FAIL'
    results = output / 'results.json'
    if results.is_file():
        data = json.loads(results.read_text(encoding='utf-8'))
        stats = data.get('stats', {})
        report.metrics['playwright'] = stats
        if result['exit_code'] == 0 and not data.get('errors'):
            verdict = ('PASS' if stats.get('expected', 0) == 7 and
                       not any(stats.get(k, 0) for k in ('unexpected', 'skipped', 'flaky')) else 'PARTIAL')
        report.artifact('playwright-json', results)
        report.artifact('playwright-html', output / 'html' / 'index.html')
    report.add('orgo.browser', verdict, 'acceptance',
               'Seven real Chromium user journeys. No mocked API. See retained artifacts for failures.', evidence=result)
