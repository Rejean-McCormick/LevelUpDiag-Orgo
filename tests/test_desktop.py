import json
import os
import tempfile
import unittest
import queue
from pathlib import Path
from unittest.mock import Mock, patch
from levelupdiag_core.desktop import save_settings, report_path, history, Session

class DesktopTests(unittest.TestCase):
    def fixture(self, root):
        tool=root/'diag'; tool.mkdir()
        target=root/'orgo'; target.mkdir()
        (target/'package.json').write_text('{}')
        (tool/'levelupdiag.config.json').write_text(json.dumps({'schema':'levelupdiag.config.v2','target_repo_root':'auto','execution':{}}))
        return tool,target

    def test_save_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'custom':'preserve','execution':{'max_parallel':2}}))
            cfg=save_settings(tool,str(target),True,False)
            self.assertEqual(cfg['custom'],'preserve')
            self.assertEqual(cfg['execution']['max_parallel'],2)
            self.assertTrue(cfg['execution']['allow_target_mutation'])
            self.assertEqual(Path(cfg['_control_root']),tool/'.levelupdiag')

    def test_invalid_target_does_not_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            with self.assertRaises(RuntimeError): save_settings(tool,str(tool),True,True)
            self.assertFalse((tool/'levelupdiag.config.local.json').exists())

    def test_report_paths_are_confined(self):
        with tempfile.TemporaryDirectory() as tmp:
            for run,relative in [('../escape','summary.json'),('safe','../../escape')]:
                with self.assertRaises(ValueError): report_path(tmp,run,relative)

    def test_corrupt_history_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'runs'/'bad'; path.mkdir(parents=True)
            (path/'summary.json').write_text('invalid')
            self.assertEqual(history(tmp),[])


    def test_native_campaign_requires_database_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            (tool/'levelupdiag_manifest.json').write_text(json.dumps({
                'schema':'levelupdiag.manifest.v2',
                'levels':[{'id':'N11','name':'db','order':0,'required':True,'depends_on':[]}],
                'campaigns':{'database':{'levels':['N11']}}
            }))
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'database':{'test_database_url':''}}))
            session=Session(tool)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, 'TEST_DATABASE_URL'):
                    session.start('database',str(target))
            self.assertFalse(session.running)


    def test_native_campaign_uses_configured_test_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            configured='postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test'
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'database':{'test_database_url':configured}}))
            (tool/'levelupdiag_manifest.json').write_text(json.dumps({
                'schema':'levelupdiag.manifest.v2',
                'levels':[{'id':'N11','name':'db','order':0,'required':True,'depends_on':[]}],
                'campaigns':{'database':{'levels':['N11']}}
            }))
            session=Session(tool)
            process = Mock()
            process.stdout = []
            process.wait.return_value = 0
            with patch.dict(os.environ, {}, clear=True), patch('levelupdiag_core.desktop.subprocess.Popen', return_value=process) as popen:
                session.start('database',str(target))
                for _ in range(100):
                    if not session.running: break
                    __import__('time').sleep(0.01)
            self.assertEqual(popen.call_args.kwargs['env']['TEST_DATABASE_URL'], configured)


    def test_acceptance_injects_browser_credentials_without_saving_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            configured='postgresql://orgo_test:orgo_test@127.0.0.1:5432/orgo_test'
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'database':{'test_database_url':configured}}))
            (tool/'levelupdiag_manifest.json').write_text(json.dumps({
                'schema':'levelupdiag.manifest.v2',
                'levels':[{'id':'N14','name':'acceptance','order':0,'required':True,'depends_on':[]}],
                'campaigns':{'acceptance':{'levels':['N14']}}
            }))
            session=Session(tool)
            process=Mock(); process.stdout=[]; process.wait.return_value=0
            browser={'url':'http://127.0.0.1:3000','organization':'orgo-e2e','email':'e2e@example.test','password':'secret-pass','allow_writes':True}
            with patch.dict(os.environ, {}, clear=True), patch('levelupdiag_core.desktop.subprocess.Popen', return_value=process) as popen:
                session.start('acceptance',str(target),browser=browser)
                for _ in range(100):
                    if not session.running: break
                    __import__('time').sleep(0.01)
            env=popen.call_args.kwargs['env']
            self.assertEqual(env['ORGO_E2E_PASSWORD'],'secret-pass')
            self.assertEqual(env['ORGO_E2E_ALLOW_WRITES'],'test-instance')
            self.assertEqual(env['TEST_DATABASE_URL'],configured)
            local=json.loads((tool/'levelupdiag.config.local.json').read_text())
            self.assertNotIn('secret-pass', json.dumps(local))

    def test_unknown_campaign_does_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            (tool/'levelupdiag_manifest.json').write_text(json.dumps({'schema':'levelupdiag.manifest.v2','levels':[{'id':'N00'}],'campaigns':{}}))
            session=Session(tool)
            with self.assertRaises(ValueError): session.start('bad',str(target))
            self.assertFalse(session.running)
