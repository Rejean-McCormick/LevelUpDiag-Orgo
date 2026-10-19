"""Tandem evidence verifier adversarial tests: no target DB, network, or Docker."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from levelupdiag_core import REPORT_SCHEMA, SUMMARY_SCHEMA, VERSION
from levelupdiag_core.evidence_integrity import (
    EvidenceError, digest_file, seal_campaign_evidence, verify_campaign_evidence,
    MAX_SUMMARY_BYTES,
)
from levelupdiag_core.util import write_json
from levelupdiag_core.verdicts import VERDICTS

ROOT = Path(__file__).resolve().parents[1]


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name) / 'runs' / '20261019T000000Z-test001'
        self.run_dir.mkdir(parents=True)
        self.run_id = self.run_dir.name
        self.report = {
            'schema': REPORT_SCHEMA, 'standard': 'LevelUpDiag', 'standard_version': VERSION,
            'run_id': self.run_id, 'level_id': 'N01', 'level_name': 'Target context',
            'purpose': 'Fixture', 'target_repo_root': '/sample/Orgo',
            'started_at': '2026-10-19T00:00:00+00:00',
            'ended_at': '2026-10-19T00:00:01+00:00', 'verdict': 'PASS',
            'findings': [], 'artifacts': [], 'metrics': {},
        }
        self.summary = {
            'schema': SUMMARY_SCHEMA, 'standard': 'LevelUpDiag', 'standard_version': VERSION,
            'run_id': self.run_id, 'selection': 'baseline', 'target_repo_root': '/sample/Orgo',
            'verdict': 'PASS', 'required_levels': ['N01'], 'expected_levels': ['N01'],
            'levels': [{'id':'N01', 'name':'Target context', 'verdict':'PASS', 'result':'levels/N01/result.json'}],
            'target_protection': None,
            'counts': {v:int(v == 'PASS') for v in VERDICTS},
        }
        self.level_path = self.run_dir / 'levels/N01/result.json'
        self.summary_path = self.run_dir / 'summary.json'
        self.save()

    def save(self):
        write_json(self.level_path, self.report)
        seal_campaign_evidence(self.run_dir, self.summary)
        write_json(self.summary_path, self.summary)

    def verify(self, pin=None):
        return verify_campaign_evidence(self.summary_path, pin)

    def test_genuine_bundle_qualifies(self):
        summary, digest = self.verify()
        self.assertEqual(summary['verdict'], 'PASS')
        self.assertEqual(len(digest), 64)
        self.assertEqual(self.verify(digest)[1], digest)

    def test_cli_fails_closed_for_modified_report(self):
        self.level_path.write_text(self.level_path.read_text() + '\n')
        cp = subprocess.run([sys.executable, str(ROOT/'levelupdiag.py'), 'verify-run', str(self.summary_path)],
                            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(cp.returncode, 30)
        self.assertIn('SHA-256 mismatch', cp.stderr)

    def test_missing_level_report_fails(self):
        self.level_path.unlink()
        with self.assertRaises((EvidenceError, OSError)):
            self.verify()

    def test_absent_legacy_manifest_fails(self):
        self.summary.pop('evidence_integrity')
        write_json(self.summary_path, self.summary)
        with self.assertRaisesRegex(EvidenceError, 'Missing integrity manifest'):
            self.verify()

    def test_fake_campaign_pass_rejected_even_if_reshashed(self):
        self.report['verdict'] = 'FAIL'
        self.summary['levels'][0]['verdict'] = 'FAIL'
        self.summary['counts'] = {v:int(v == 'FAIL') for v in VERDICTS}
        self.save()  # Recompute all mutable hashes; verdict still inconsistent.
        with self.assertRaisesRegex(EvidenceError, 'Campaign verdict mismatch'):
            self.verify()

    def test_optional_observed_fail_is_still_fail(self):
        self.report['verdict'] = 'FAIL'
        self.summary['levels'][0]['verdict'] = 'FAIL'
        self.summary['required_levels'] = []
        self.summary['counts'] = {v:int(v == 'FAIL') for v in VERDICTS}
        self.save()
        with self.assertRaisesRegex(EvidenceError, 'Campaign verdict mismatch'):
            self.verify()

    def test_required_skip_cannot_make_pass(self):
        self.report['verdict'] = 'SKIP'
        self.summary['levels'][0]['verdict'] = 'SKIP'
        self.summary['counts'] = {v:int(v == 'SKIP') for v in VERDICTS}
        self.save()
        with self.assertRaisesRegex(EvidenceError, 'Campaign verdict mismatch'):
            self.verify()

    def test_target_protection_failure_cannot_claim_pass(self):
        self.summary['target_protection'] = {'verdict':'ERROR'}
        write_json(self.summary_path, self.summary)
        with self.assertRaisesRegex(EvidenceError, 'Campaign verdict mismatch'):
            self.verify()

    def test_external_anchor_rejects_rewritten_entire_bundle(self):
        pin = self.verify()[1]
        self.report['verdict'] = 'WARN'
        self.summary['levels'][0]['verdict'] = 'WARN'
        self.summary['verdict'] = 'WARN'
        self.summary['counts'] = {v:int(v == 'WARN') for v in VERDICTS}
        self.save()
        self.assertEqual(self.verify()[0]['verdict'], 'WARN')
        with self.assertRaisesRegex(EvidenceError, 'external SHA-256 pin'):
            self.verify(pin)

    def test_summary_report_tenant_target_mismatch(self):
        self.report['target_repo_root'] = '/another/tenant'
        self.save()
        with self.assertRaisesRegex(EvidenceError, 'target_repo_root'):
            self.verify()

    def test_run_id_mismatch(self):
        self.summary['run_id'] = 'another-run'
        write_json(self.summary_path, self.summary)
        with self.assertRaisesRegex(EvidenceError, 'run_id'):
            self.verify()

    def test_report_duplicate_or_path_traversal_rejected(self):
        self.summary['levels'][0]['result'] = '../../elsewhere.json'
        write_json(self.summary_path, self.summary)
        with self.assertRaisesRegex(EvidenceError, 'Unsafe'):
            self.verify()

    def test_deleted_manifest_entry_rejected(self):
        self.summary['evidence_integrity']['files'].clear()
        write_json(self.summary_path, self.summary)
        with self.assertRaisesRegex(EvidenceError, 'exactly'):
            self.verify()

    def test_counts_cannot_lie(self):
        self.summary['counts']['PASS'] = 0
        write_json(self.summary_path, self.summary)
        with self.assertRaisesRegex(EvidenceError, 'counts'):
            self.verify()

    def test_malformed_required_levels_is_refused_not_crash(self):
        self.summary['required_levels'] = [{}]
        write_json(self.summary_path, self.summary)
        with self.assertRaises(EvidenceError):
            self.verify()

    def test_symlinked_level_result_rejected(self):
        real = self.run_dir / 'real.json'
        real.write_bytes(self.level_path.read_bytes())
        self.level_path.unlink()
        try:
            self.level_path.symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest('Creating symlinks unavailable')
        with self.assertRaises(EvidenceError):
            self.verify()

    def test_cli_validates_externally_pinned_summary(self):
        pin = digest_file(self.summary_path, MAX_SUMMARY_BYTES)
        cp = subprocess.run([sys.executable, str(ROOT/'levelupdiag.py'), 'verify-run', str(self.summary_path),
                             '--expected-summary-sha256', pin], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn('VALID: PASS', cp.stdout)
        self.assertNotIn('not independently authenticated', cp.stdout)

if __name__ == '__main__':
    unittest.main()
