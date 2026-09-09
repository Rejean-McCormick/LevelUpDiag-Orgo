import sys, tempfile, unittest
from pathlib import Path
from levelupdiag_core.commands import run_command

class CommandTests(unittest.TestCase):
    def test_argument_array_no_shell(self):
        with tempfile.TemporaryDirectory() as d:
            r=run_command([sys.executable,"-c","print('ok')"],cwd=Path(d),timeout_seconds=10)
            self.assertEqual(r["exit_code"],0)
            self.assertIn("ok",r["stdout_tail"])

    def test_timeout_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_command([sys.executable, '-c', 'import time; time.sleep(30)'], cwd=Path(d), timeout_seconds=0.05)
            self.assertTrue(r['timed_out'])
            self.assertIsNone(r['exit_code'])

    def test_large_output_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_command([sys.executable, '-c', "print('x'*1000000)"], cwd=Path(d), timeout_seconds=10, capture_limit_kb=1)
            self.assertLess(len(r['stdout_tail']), 1100)
            self.assertEqual(r['exit_code'], 0)
