import json
import tempfile
import unittest
from pathlib import Path
from levelupdiag_core.config import load_config, ConfigError, DEFAULT_TEST_DATABASE_URL

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


    def test_target_dotenv_database_is_loaded_in_memory_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'orgo'; target.mkdir()
            (target/'.env').write_text(
                'POSTGRES_PASSWORD=p%40ss word\n'
                'ORGO_ADMIN_PASSWORD=Browser-Test!2026#safe\n'
                'ORGO_ADMIN_EMAIL=e2e@example.test\n'
                'ORGO_ORGANIZATION=orgo-e2e\n'
            )
            tool = self.setup_paths(root, str(target))
            cfg = load_config(tool)
            self.assertIn('postgresql://orgo:', cfg['_target_env_database_url'])
            self.assertTrue(cfg['_target_env_has_postgres_password'])
            self.assertEqual(cfg['_target_env_browser_password'], 'Browser-Test!2026#safe')
            self.assertEqual(cfg['_target_env_browser_email'], 'e2e@example.test')
            self.assertEqual(cfg['_target_env_browser_organization'], 'orgo-e2e')
            self.assertEqual(cfg['database']['test_database_url'], DEFAULT_TEST_DATABASE_URL)
            saved = json.loads((tool/'levelupdiag.config.json').read_text())
            self.assertNotIn('database', saved)
            self.assertNotIn('Browser-Test!2026#safe', (tool/'levelupdiag.config.json').read_text())

    def test_target_dotenv_path_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'orgo'; target.mkdir()
            tool = self.setup_paths(root, str(target))
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'database':{'target_env_file':'../outside.env'}}))
            with self.assertRaises(ConfigError):
                load_config(tool)

    def test_report_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'orgo'; target.mkdir()
            tool = self.setup_paths(root, str(target))
            (tool/'levelupdiag.config.local.json').write_text(json.dumps({'control_dir':'../orgo'}))
            with self.assertRaises(ConfigError): load_config(tool)
