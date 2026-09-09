import json
import tempfile
import unittest
from pathlib import Path
from levelupdiag_core.config import load_config, ConfigError

class StandaloneTests(unittest.TestCase):
    def setup_paths(self, root, target='auto'):
        tool = root/'diagnostic'
        tool.mkdir()
        (tool/'levelupdiag.config.json').write_text(json.dumps({
            'schema':'levelupdiag.config.v2','target_repo_root':target,'control_dir':'.levelupdiag'}))
        return tool

    def test_explicit_target_required(self):
        with tempfile.TemporaryDirectory() as d:
            tool = self.setup_paths(Path(d))
            with self.assertRaises(ConfigError): load_config(tool)

    def test_reports_remain_in_diagnostic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root/'orgo'; target.mkdir()
            tool = self.setup_paths(root, str(target))
            cfg = load_config(tool)
            self.assertEqual(Path(cfg['_control_root']), tool/'.levelupdiag')
            self.assertFalse((target/'.levelupdiag').exists())

    def test_nested_repositories_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); tool = self.setup_paths(root)
            for target in (root, tool):
                with self.assertRaises(ConfigError): load_config(tool, str(target))

    def test_report_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'orgo'; target.mkdir()
            tool = self.setup_paths(root, str(target))
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'control_dir':'../orgo'}))
            with self.assertRaises(ConfigError): load_config(tool)
