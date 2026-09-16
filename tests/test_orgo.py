import os
import tempfile
import unittest
import subprocess
import sys
import json
import threading
import time
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from levelupdiag_core.report import Report
from levelupdiag_core.util import redact
from levelupdiag_core.util import read_json
from levelupdiag_core.manifest import load_manifest, resolve_selection
from levelupdiag_core.runner import HARD_DEP_BLOCK
from levelupdiag_core.runner import run_campaign
from levels.orgo_validation import run, test_database_valid

class OrgoTests(unittest.TestCase):
    def report(self, level):
        return Report(level, level, 'test', '.', 'test')

    def test_database_guard(self):
        for url in ('', 'invalid', 'https://host/orgo_test', 'postgresql://host/latest', 'postgresql://host/prod'):
            self.assertFalse(test_database_valid(url))
        self.assertTrue(test_database_valid('postgresql://localhost/orgo_test'))

    def test_mutation_disabled_does_not_launch(self):
        report = self.report('N08')
        with patch('levels.orgo_validation.run_command') as command:
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.'}, report)
        command.assert_not_called()
        self.assertEqual(report.to_dict()['verdict'], 'BLOCKED')

    def test_native_requires_explicit_test_database(self):
        report = self.report('N11')
        with patch.dict(os.environ, {'DATABASE_URL':'postgresql://localhost/production'}, clear=True), patch('levels.orgo_validation.run_command') as command:
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.', 'execution':{'allow_target_mutation':True,'allow_network':True}}, report)
        command.assert_not_called()
        self.assertEqual(report.to_dict()['verdict'], 'BLOCKED')

    def test_audit_respects_network_gate(self):
        report = self.report('N13')
        with patch('levels.orgo_validation.run_command') as command:
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.'}, report)
        command.assert_not_called()
        self.assertEqual(report.to_dict()['verdict'], 'BLOCKED')

    def test_failure_stops_dependent_steps(self):
        report = self.report('N08')
        with patch('levels.orgo_validation.run_command', return_value={'timed_out':False,'exit_code':1}) as command:
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.','execution':{'allow_target_mutation':True}}, report)
        self.assertEqual(command.call_count, 1)
        self.assertEqual(report.to_dict()['verdict'], 'FAIL')

    def test_timeout_is_infrastructure_failure(self):
        report = self.report('N09')
        with patch('levels.orgo_validation.run_command', return_value={'timed_out':True,'exit_code':None}):
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.','execution':{'allow_target_mutation':True}}, report)
        self.assertEqual(report.to_dict()['verdict'], 'INFRA_ERROR')

    def test_pglite_is_not_native_acceptance(self):
        report = self.report('N10')
        with patch('levels.orgo_validation.run_command', return_value={'timed_out':False,'exit_code':0,'stdout_tail':'# tests 34\n# pass 33\n# skipped 1\n'}):
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.','execution':{'allow_target_mutation':True}}, report)
        self.assertEqual(report.to_dict()['verdict'], 'WARN')

    def test_zero_tests_is_not_success(self):
        report = self.report('N09')
        with patch('levels.orgo_validation.run_command', return_value={'timed_out':False,'exit_code':0,'stdout_tail':''}):
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.','execution':{'allow_target_mutation':True}}, report)
        self.assertEqual(report.to_dict()['verdict'], 'PARTIAL')

    def test_native_skipped_tests_block_acceptance(self):
        report = self.report('N11')
        results = [{'timed_out':False,'exit_code':0,'stdout_tail':'migrations done'},
                   {'timed_out':False,'exit_code':0,'stdout_tail':'# tests 34\n# pass 33\n# skipped 1\n'}]
        with patch.dict(os.environ, {'TEST_DATABASE_URL':'postgresql://localhost/orgo_test'}), patch('levels.orgo_validation.run_command', side_effect=results):
            run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.','execution':{'allow_target_mutation':True,'allow_network':True}}, report)
        self.assertEqual(report.to_dict()['verdict'], 'PARTIAL')

    def test_manual_acceptance_cannot_be_green(self):
        report = self.report('N14')
        run({'_tool_root':str(Path(__file__).resolve().parents[1]),'_target_root':'.'}, report)
        self.assertEqual(report.to_dict()['verdict'], 'BLOCKED')

    def test_database_secrets_redacted(self):
        with patch.dict(os.environ, {'API_TOKEN':'veryprivate'}):
            result = redact('postgresql://user:pass@localhost/test Bearer abcdefghi veryprivate')
        for secret in ('user:pass', 'abcdefghi', 'veryprivate'):
            self.assertNotIn(secret, result)

    def test_campaign_dependencies(self):
        manifest = load_manifest(Path(__file__).resolve().parents[1])
        ids = [m['id'] for m in resolve_selection(manifest, 'deep')]
        for required in ('N07', 'N08', 'N09', 'N11', 'N12', 'N13'):
            self.assertIn(required, ids)
        self.assertLess(ids.index('N08'), ids.index('N11'))
        self.assertTrue({'FAIL','SKIP','PARTIAL'} <= HARD_DEP_BLOCK)

    def test_windows_bom_config(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'config.json'
            file.write_text('{"enabled":true}', encoding='utf-8-sig')
            self.assertTrue(read_json(file)['enabled'])

    def test_exclusive_level_never_overlaps_parallel_work(self):
        manifest = {'levels': [
            {'id':'A','name':'A','order':0,'required':True,'parallel_safe':False},
            {'id':'B','name':'B','order':1,'required':True,'parallel_safe':True},
        ], 'campaigns': {'test': {'levels':['A','B']}}}
        active, overlaps = set(), []
        lock = threading.Lock()
        def worker(command, **kwargs):
            lid = command[command.index('--level')+1]
            output = Path(command[command.index('--output')+1])
            with lock:
                if active: overlaps.append((lid, tuple(active)))
                active.add(lid)
            time.sleep(0.08)
            output.write_text(json.dumps({'level_id':lid,'level_name':lid,'verdict':'PASS','metrics':{}}))
            with lock: active.remove(lid)
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        with tempfile.TemporaryDirectory() as directory:
            cfg = {'_target_root':directory,'_control_root':str(Path(directory)/'reports'),
                   'execution':{'protect_tracked_files':False,'max_parallel':2}}
            with patch('levelupdiag_core.runner.load_manifest', return_value=manifest), patch('levelupdiag_core.runner.load_config', return_value=cfg), patch('levelupdiag_core.runner.subprocess.run', side_effect=worker):
                summary, code, _ = run_campaign(Path(directory), 'test')
            self.assertEqual(code, 0)
            self.assertEqual(overlaps, [])


    def test_generated_tracked_file_restoration_prevents_false_vcs_error(self):
        manifest = {'levels': [
            {'id':'A','name':'A','order':0,'required':True,'parallel_safe':True},
        ], 'campaigns': {'test': {'levels':['A']}}}
        before = {'repository': True, 'tracked_status': ''}
        after = {'repository': True, 'tracked_status': ''}
        def worker(command, **kwargs):
            output = Path(command[command.index('--output')+1])
            output.write_text(json.dumps({'level_id':'A','level_name':'A','verdict':'PASS','metrics':{}}))
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        with tempfile.TemporaryDirectory() as directory:
            cfg = {'_target_root':directory,'_control_root':str(Path(directory)/'reports'),
                   'execution':{'protect_tracked_files':True,'max_parallel':1,
                                'restore_generated_tracked_files':['apps/web/next-env.d.ts']}}
            with patch('levelupdiag_core.runner.load_manifest', return_value=manifest), \
                 patch('levelupdiag_core.runner.load_config', return_value=cfg), \
                 patch('levelupdiag_core.runner.subprocess.run', side_effect=worker), \
                 patch('levelupdiag_core.runner.git_info', side_effect=[before, after]), \
                 patch('levelupdiag_core.runner.snapshot_tracked_files', return_value={'apps/web/next-env.d.ts': {'content': b'x', 'mode': 0o644}}), \
                 patch('levelupdiag_core.runner.restore_tracked_files', return_value=['apps/web/next-env.d.ts']):
                summary, code, _ = run_campaign(Path(directory), 'test')
            self.assertEqual(code, 0)
            self.assertEqual(summary['verdict'], 'PASS')
            self.assertEqual(summary['target_protection']['verdict'], 'PASS')
            self.assertEqual(summary['target_protection']['restored_files'], ['apps/web/next-env.d.ts'])

    def test_blocked_campaign_persists_all_level_reports(self):
        tool = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(tool/'levelupdiag.py'), '--target', directory, 'run', 'quick'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 20, result.stdout+result.stderr)
            summary = read_json(tool/'.levelupdiag/latest/summary.json')
            self.assertEqual(summary['verdict'], 'BLOCKED')
            for level in summary['levels']:
                self.assertTrue((tool/'.levelupdiag/latest'/level['id']/'result.json').exists())
