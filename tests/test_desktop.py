import json
import tempfile
import unittest
import queue
from pathlib import Path
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

    def test_unknown_campaign_does_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool,target=self.fixture(Path(tmp))
            (tool/'levelupdiag_manifest.json').write_text(json.dumps({'schema':'levelupdiag.manifest.v2','levels':[{'id':'N00'}],'campaigns':{}}))
            session=Session(tool)
            with self.assertRaises(ValueError): session.start('bad',str(target))
            self.assertFalse(session.running)
