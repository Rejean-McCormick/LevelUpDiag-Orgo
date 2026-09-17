import unittest
from levelupdiag_core.desktop import browser_environment, browser_defaults_from_config


class BrowserSettingsTests(unittest.TestCase):
    def settings(self, **overrides):
        return dict(dict(url='http://127.0.0.1:3000', organization='orgo-e2e',
                         email='e2e@example.test', password='test password', allow_writes=True), **overrides)

    def test_local_settings_are_mapped_without_modifying_input(self):
        settings = self.settings()
        before = settings.copy()
        env = browser_environment(settings)
        self.assertEqual(env['ORGO_E2E_PASSWORD'], 'test password')
        self.assertEqual(env['ORGO_E2E_ALLOW_WRITES'], 'test-instance')
        self.assertEqual(settings, before)

    def test_disallows_remote_or_credentialed_urls(self):
        for url in ['https://example.com', 'http://localhost.example.com',
                    'http://user:secret@localhost:3000', 'http://localhost:bad',
                    'http://localhost:3000/path', 'http://localhost:3000?token=secret']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                browser_environment(self.settings(url=url))

    def test_missing_credentials_or_consent_cannot_launch(self):
        for key in ['organization', 'email', 'password', 'allow_writes']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                browser_environment(self.settings(**{key: ''}))

    def test_browser_defaults_use_target_env_admin_account(self):
        cfg = {
            '_target_env_browser_organization': 'orgo-e2e',
            '_target_env_browser_email': 'e2e@example.test',
            '_target_env_browser_password': 'from-dotenv-secret',
        }
        defaults = browser_defaults_from_config(cfg)
        self.assertEqual(defaults['organization'], 'orgo-e2e')
        self.assertEqual(defaults['email'], 'e2e@example.test')
        self.assertEqual(defaults['password'], 'from-dotenv-secret')

    def test_browser_defaults_do_not_invent_password(self):
        defaults = browser_defaults_from_config({})
        self.assertEqual(defaults['organization'], 'orgo-e2e')
        self.assertEqual(defaults['email'], 'e2e@example.test')
        self.assertEqual(defaults['password'], '')

