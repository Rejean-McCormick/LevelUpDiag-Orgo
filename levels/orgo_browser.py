"""Real browser acceptance against an explicitly selected local test instance."""
import json
import os
from pathlib import Path
from levelupdiag_core.commands import run_command


def coverage_verdict(data, coverage, exit_code):
    expected = coverage['required_titles']
    if not expected or len(set(expected)) != len(expected):
        raise ValueError('Browser coverage must contain unique required titles.')
    executed = []
    def visit(suite):
        for spec in suite.get('specs', []):
            for test in spec.get('tests', []):
                executed.append((spec.get('title'), test.get('projectName'), test.get('status')))
        for child in suite.get('suites', []): visit(child)
    for suite in data.get('suites', []): visit(suite)
    stats = data.get('stats', {})
    if exit_code != 0 or data.get('errors') or stats.get('unexpected', 0):
        return 'FAIL'
    actual = [(title, project) for title, project, status in executed]
    required = [(title, coverage['project']) for title in expected]
    if (sorted(actual) != sorted(required) or stats.get('expected') != len(expected)
            or any(stats.get(k, 0) for k in ('skipped', 'flaky'))
            or any(status != 'expected' for _, _, status in executed)):
        return 'PARTIAL'
    return 'PASS'


def run(cfg, report):
    execution = cfg.get('execution', {})
    required = ['ORGO_E2E_ORGANIZATION', 'ORGO_E2E_EMAIL', 'ORGO_E2E_PASSWORD']
    missing = [key for key in required if not os.environ.get(key)]
    browser = Path(cfg['_tool_root']) / 'browser'
    cli = browser / 'node_modules' / '@playwright' / 'test' / 'cli.js'
    coverage = json.loads((browser / 'coverage.json').read_text(encoding='utf-8'))
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
    result = run_command(['node', str(cli), 'test'], cwd=browser, timeout_seconds=1800, env=env)
    verdict = 'INFRA_ERROR' if result['timed_out'] else 'FAIL'
    results = output / 'results.json'
    if results.is_file():
        data = json.loads(results.read_text(encoding='utf-8'))
        stats = data.get('stats', {})
        report.metrics['playwright'] = stats
        report.metrics['required_browser_tests'] = len(coverage['required_titles'])
        if not result['timed_out']:
            verdict = coverage_verdict(data, coverage, result['exit_code'])
        report.artifact('playwright-json', results)
        report.artifact('playwright-html', output / 'html' / 'index.html')
    report.add('orgo.browser', verdict, 'acceptance',
               f"{len(coverage['required_titles'])} required Chromium journeys; real API, no network mocks. See retained artifacts for failures.", evidence=result)
