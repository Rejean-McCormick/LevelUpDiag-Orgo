import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from levelupdiag_core.test_runtime import TestRuntime, cli_path, api_is_ready, TEST_DATABASE


class RuntimeTests(unittest.TestCase):
    def test_readiness_accepts_orgo_envelope_and_plain_response(self):
        self.assertTrue(api_is_ready({'ok': True, 'data': {'status': 'ready'}, 'error': None}))
        self.assertTrue(api_is_ready({'status': 'ready'}))

    def test_readiness_rejects_failed_or_malformed_payload(self):
        for payload in [None, [], {}, {'ok': False, 'data': {'status': 'ready'}},
                        {'ok': True, 'data': None}, {'status': 'alive'},
                        {'ok': True, 'data': {'status': 'unavailable'}}]:
            with self.subTest(payload=payload):
                self.assertFalse(api_is_ready(payload))

    def test_wait_ready_returns_on_first_healthy_enveloped_response(self):
        runtime = TestRuntime('.')
        process = Mock()
        process.poll.return_value = None
        response = Mock()
        response.status = 200
        response.read.return_value = b'{"ok":true,"data":{"status":"ready"},"error":null}'
        with patch('levelupdiag_core.test_runtime.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = response
            runtime.wait_ready('http://127.0.0.1:4000/health/ready', process, 1, api=True)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_cli_resolves_workspace_before_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cli = root / 'apps/api/node_modules/tsx/dist/cli.mjs'
            cli.parent.mkdir(parents=True)
            cli.touch()
            self.assertEqual(cli_path(root, 'api', 'tsx', 'dist/cli.mjs'), cli)

    def test_missing_dependency_has_clear_error(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, 'npm ci'):
            cli_path(Path(folder), 'api', 'tsx', 'dist/cli.mjs')



    def test_docker_error_reports_redacted_stderr(self):
        runtime = TestRuntime('.')
        result = Mock(returncode=1, stdout='', stderr='connection postgresql://user:password@localhost/db failed')
        with patch('levelupdiag_core.test_runtime.subprocess.run', return_value=result):
            with self.assertRaises(RuntimeError) as caught:
                runtime.docker('exec', 'orgo-test-postgres', 'false')
        message = str(caught.exception)
        self.assertIn('exit 1', message)
        self.assertIn('<REDACTED>@localhost/db', message)
        self.assertNotIn('user:password@', message)

    def test_managed_database_starts_validated_container(self):
        runtime = TestRuntime('.')
        info = [{
            'Config': {'Env': ['POSTGRES_DB=orgo_test', 'POSTGRES_USER=orgo_test', 'POSTGRES_PASSWORD=orgo_test']},
            'HostConfig': {'PortBindings': {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '5432'}]}},
        }]
        with patch.object(runtime, 'docker', side_effect=[json.dumps(info), '', '']) as docker:
            self.assertEqual(runtime.ensure_database(), TEST_DATABASE)
        self.assertEqual(docker.call_args_list[0].args, ('inspect', 'orgo-test-postgres'))
        self.assertEqual(docker.call_args_list[1].args, ('start', 'orgo-test-postgres'))
        self.assertEqual(docker.call_args_list[2].args[:3], ('exec', 'orgo-test-postgres', 'pg_isready'))


    def test_reset_database_recreates_only_orgo_test(self):
        runtime = TestRuntime('.')
        info = [{
            'Config': {'Env': ['POSTGRES_DB=orgo_test', 'POSTGRES_USER=orgo_test', 'POSTGRES_PASSWORD=orgo_test']},
            'HostConfig': {'PortBindings': {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '5432'}]}},
        }]
        outputs = [json.dumps(info), '', '', '', '', '', '']
        with patch.object(runtime, 'docker', side_effect=outputs) as docker:
            self.assertEqual(runtime.reset_database(), TEST_DATABASE)
        calls = [call.args for call in docker.call_args_list]
        self.assertIn(('exec', 'orgo-test-postgres', 'dropdb', '-U', 'orgo_test', '--if-exists', 'orgo_test'), calls)
        self.assertIn(('exec', 'orgo-test-postgres', 'createdb', '-U', 'orgo_test', 'orgo_test'), calls)
        self.assertTrue(any(call[:3] == ('exec', 'orgo-test-postgres', 'psql') and 'pg_terminate_backend' in call[-1] for call in calls))
        self.assertFalse(any('orgo' == arg for call in calls for arg in call if call[:3] == ('exec', 'orgo-test-postgres', 'dropdb')))

    def test_cleanup_does_not_kill_already_exited_process(self):
        runtime = TestRuntime('.')
        process = Mock()
        process.poll.return_value = 0
        runtime.processes = [process]
        with patch('levelupdiag_core.test_runtime.subprocess.run') as run:
            runtime.cleanup()
        run.assert_not_called()
        self.assertEqual(runtime.processes, [])

    def test_busy_stop_cancels_startup(self):
        runtime = TestRuntime('.')
        runtime.busy = True
        runtime.stop()
        self.assertTrue(runtime.cancel.is_set())

    def test_occupied_port_prevents_process_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            main = target / 'apps/api/src/main.ts'
            main.parent.mkdir(parents=True)
            main.touch()
            runtime = TestRuntime(target)
            with patch('levelupdiag_core.test_runtime.shutil.which', return_value='node'), \
                 patch('levelupdiag_core.test_runtime.cli_path', return_value=main), \
                 patch('levelupdiag_core.test_runtime.occupied', return_value=True), \
                 patch('levelupdiag_core.test_runtime.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError, 'occupied'):
                    runtime.start(target)
                launch.assert_not_called()
