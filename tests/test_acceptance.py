import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from levelupdiag_core.report import Report
from levels import orgo_acceptance


class AcceptanceTests(unittest.TestCase):
    def report(self):
        return Report('N14','N14','test','.', '20260916T000000Z-abc12345')

    def test_policy_gate_blocks_before_docker(self):
        report=self.report()
        with patch('levels.orgo_acceptance.backup_restore_acceptance') as backup:
            orgo_acceptance.run({'execution':{},'_target_root':'.','_tool_root':'.'}, report)
        backup.assert_not_called()
        self.assertEqual(report.to_dict()['verdict'],'BLOCKED')

    def test_core_acceptance_can_pass_with_no_external_provider(self):
        report=self.report()
        cfg={'execution':{'allow_target_mutation':True,'allow_network':True},
             '_target_root':'.','_tool_root':'.','_target_env_configured_providers':[]}
        with patch('levels.orgo_acceptance.backup_restore_acceptance', return_value=True), \
             patch('levels.orgo_acceptance.deployment_and_browser_acceptance', return_value=True):
            orgo_acceptance.run(cfg, report)
        self.assertEqual(report.to_dict()['verdict'],'PASS')

    def test_external_provider_keeps_core_acceptance_non_green(self):
        report=self.report()
        cfg={'execution':{'allow_target_mutation':True,'allow_network':True},
             '_target_root':'.','_tool_root':'.','_target_env_configured_providers':['kristal']}
        with patch('levels.orgo_acceptance.backup_restore_acceptance', return_value=True), \
             patch('levels.orgo_acceptance.deployment_and_browser_acceptance', return_value=True):
            orgo_acceptance.run(cfg, report)
        self.assertEqual(report.to_dict()['verdict'],'WARN')


    def test_backup_restore_is_confined_to_managed_container_and_temp_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            scripts=target/'scripts/operations'; scripts.mkdir(parents=True)
            (scripts/'backup.sh').write_text('#!/usr/bin/env bash\n')
            (scripts/'restore.sh').write_text('#!/usr/bin/env bash\n')
            report=self.report()
            cfg={'_target_root':str(target),'_tool_root':str(target)}
            managed='postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test'
            with patch.dict(os.environ, {'TEST_DATABASE_URL':managed}, clear=True), \
                 patch('levels.orgo_acceptance.shutil.which', return_value='docker'), \
                 patch('levels.orgo_acceptance.TestRuntime.ensure_database', return_value=managed), \
                 patch('levels.orgo_acceptance.TestRuntime.docker', return_value='') as docker, \
                 patch('levels.orgo_acceptance._query_count', side_effect=[12,12,1,1]):
                self.assertTrue(orgo_acceptance.backup_restore_acceptance(cfg, report))
            calls=[call.args for call in docker.call_args_list]
            self.assertTrue(any(call[:2]==('cp', str(scripts/'backup.sh')) for call in calls))
            self.assertTrue(any(call[:3]==('exec','orgo-test-postgres','createdb') and '-T' in call and 'template0' in call and 'orgo_restore_validation_' in call[-1] for call in calls))
            self.assertFalse(any(call[:3]==('exec','orgo-test-postgres','dropdb') and call[-1]=='orgo' for call in calls))
            self.assertEqual(report.to_dict()['verdict'],'PASS')


    def test_backup_restore_failure_reports_stage_and_redacted_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            scripts=target/'scripts/operations'; scripts.mkdir(parents=True)
            (scripts/'backup.sh').write_text('#!/usr/bin/env bash\n')
            (scripts/'restore.sh').write_text('#!/usr/bin/env bash\n')
            report=self.report()
            cfg={'_target_root':str(target),'_tool_root':str(target)}
            managed='postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test'
            with patch.dict(os.environ, {'TEST_DATABASE_URL':managed, 'ORGO_ADMIN_PASSWORD':'super-secret-value'}, clear=True), \
                 patch('levels.orgo_acceptance.shutil.which', return_value='docker'), \
                 patch('levels.orgo_acceptance.TestRuntime.ensure_database', return_value=managed), \
                 patch('levels.orgo_acceptance.TestRuntime.docker', side_effect=RuntimeError('failed super-secret-value')):
                self.assertFalse(orgo_acceptance.backup_restore_acceptance(cfg, report))
            finding=report.findings[0]
            self.assertEqual(finding['evidence']['stage'], 'copy-backup-script')
            self.assertNotIn('super-secret-value', str(finding['evidence']))
            self.assertIn('<REDACTED>', str(finding['evidence']))

    def test_deployment_uses_dynamic_host_ports_and_browser_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp); (target/'docker-compose.yml').write_text('services: {}\n')
            report=self.report()
            cfg={'_target_root':str(target),'_control_root':str(target/'control'),'_tool_root':str(target)}
            seen_envs=[]
            def command(argv, **kwargs):
                seen_envs.append(dict(kwargs.get('env') or {}))
                stdout='postgres\napi\nworker\nweb\n' if 'ps' in argv else ''
                return {'exit_code':0,'timed_out':False,'stdout_tail':stdout,'stderr_tail':''}
            def browser(_cfg, browser_report):
                self.assertEqual(os.environ.get('ORGO_E2E_URL'), 'http://127.0.0.1:49112')
                browser_report.add('orgo.browser.playwright','PASS','browser','ok')
            env={
                'ORGO_E2E_PASSWORD':'pw12345',
                'ORGO_E2E_EMAIL':'e2e@example.test',
                'ORGO_E2E_ORGANIZATION':'orgo-e2e',
                'ORGO_E2E_ALLOW_WRITES':'test-instance',
            }
            with patch.dict(os.environ, env, clear=True), \
                 patch('levels.orgo_acceptance.shutil.which', return_value='docker'), \
                 patch('levels.orgo_acceptance._free_local_port', side_effect=[49111,49112]), \
                 patch('levels.orgo_acceptance._http_ready', return_value=True), \
                 patch('levels.orgo_acceptance.run_command', side_effect=command), \
                 patch('levels.orgo_acceptance.orgo_browser.run', side_effect=browser):
                self.assertTrue(orgo_acceptance.deployment_and_browser_acceptance(cfg, report))
            self.assertTrue(any(e.get('ORGO_API_HOST_PORT')=='49111' and e.get('ORGO_WEB_HOST_PORT')=='49112' for e in seen_envs))
            deployment=next(item for item in report.findings if item['id']=='orgo.acceptance.deployment')
            self.assertEqual(deployment['evidence']['api_host_port'], 49111)
            self.assertEqual(deployment['evidence']['web_host_port'], 49112)

    def test_compose_environment_blanks_external_endpoints(self):
        report=self.report()
        with patch.dict(os.environ, {
            'ORGO_E2E_PASSWORD':'pw12345','ORGO_E2E_EMAIL':'e2e@example.test',
            'ORGO_E2E_ORGANIZATION':'orgo-e2e','KRISTAL_BRIDGE_URL':'https://live.invalid',
            'OIDC_ISSUER':'https://issuer.invalid'
        }, clear=True):
            env=orgo_acceptance._compose_env(report, 49111, 49112)
        self.assertEqual(env['KRISTAL_BRIDGE_URL'],'')
        self.assertEqual(env['OIDC_ISSUER'],'')
        self.assertEqual(env['ORGO_ADMIN_PASSWORD'],'pw12345')
        self.assertEqual(env['ORGO_ADMIN_EMAIL'],'e2e@example.test')
        self.assertEqual(env['ORGO_API_HOST_PORT'],'49111')
        self.assertEqual(env['ORGO_WEB_HOST_PORT'],'49112')
        self.assertEqual(env['ORGO_PUBLIC_URL'],'http://127.0.0.1:49112')

    def test_free_local_ports_are_distinct_and_bindable(self):
        first=orgo_acceptance._free_local_port()
        second=orgo_acceptance._free_local_port({first})
        self.assertNotEqual(first, second)
        self.assertGreater(first, 0)
        self.assertGreater(second, 0)

