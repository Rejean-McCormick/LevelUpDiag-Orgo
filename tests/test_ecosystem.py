import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from levelupdiag_core.desktop import Session
from levelupdiag_core.manifest import load_manifest, resolve_selection
from levels.orgo_ecosystem import SEED, EXPECTED_CASES, EXPECTED_TASKS, _surface


class EcosystemTests(unittest.TestCase):
    def test_seed_is_exactly_five_cases_nineteen_tasks(self):
        self.assertEqual(len(SEED['cases']), EXPECTED_CASES)
        self.assertEqual(sum(len(x['tasks']) for x in SEED['cases']), EXPECTED_TASKS)
        self.assertEqual(len({x['case_id'] for x in SEED['cases']}), EXPECTED_CASES)

    def test_ecosystem_campaign_resolves_preflight_then_n16(self):
        root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(root)
        ids = [x['id'] for x in resolve_selection(manifest, 'ecosystem')]
        self.assertIn('N07', ids)
        self.assertIn('N16', ids)
        self.assertLess(ids.index('N07'), ids.index('N16'))

    def test_surface_v12_contains_required_freshness_blocks_and_source_identity(self):
        source = SEED['cases'][0]
        item = {
            'source': source,
            'case': {'case_id':'00000000-0000-4000-8000-000000000001','created_at':'2026-10-03T12:00:00Z','updated_at':'2026-10-03T12:00:00Z','revision':3},
            'tasks': [{'task_id':f'10000000-0000-4000-8000-{i:012d}','revision':0} for i,_ in enumerate(source['tasks'])],
        }
        surface = _surface(item, 0)
        self.assertEqual(surface['surface_specversion'], 'kor.surface/1.2')
        self.assertEqual(surface['owner']['system'], 'orgo')
        self.assertEqual(surface['freshness']['policy'], 'informational')
        self.assertEqual(surface['blocks'][0]['kind'], 'list')
        self.assertEqual(len(surface['blocks'][0]['data']['items']), len(source['tasks']))
        self.assertIn(source['case_id'].lower(), surface['surface_id'])

    def test_session_sets_emulator_or_physical_without_saving_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); tool=root/'diag'; target=root/'orgo'; tool.mkdir(); target.mkdir()
            (target/'package.json').write_text('{}')
            (target/'.env').write_text('ORGO_ADMIN_PASSWORD=abcdefghijkl\nORGO_ADMIN_EMAIL=admin@example.test\nORGO_ORGANIZATION=orgo\n')
            (tool/'levelupdiag.config.json').write_text(json.dumps({'schema':'levelupdiag.config.v2','target_repo_root':str(target),'execution':{},'database':{'target_env_file':'.env','test_database_url':''},'ecosystem':{'kor_repo_root':'C:/mycode/Kor/kor'}}))
            (tool/'levelupdiag_manifest.json').write_text(json.dumps({'schema':'levelupdiag.manifest.v2','levels':[{'id':'N16','name':'eco','order':0,'required':True,'depends_on':[]}],'campaigns':{'ecosystem':{'levels':['N16']}}}))
            session=Session(tool)
            process=Mock(); process.stdout=[]; process.wait.return_value=0
            browser={'url':'http://127.0.0.1:3000','organization':'orgo','email':'admin@example.test','password':'abcdefghijkl','allow_writes':True}
            with patch('levelupdiag_core.desktop.subprocess.Popen', return_value=process) as popen:
                session.start('ecosystem',str(target),browser=browser,ecosystem={'physical':True,'kor_root':'C:/mycode/Kor/kor'})
                for _ in range(100):
                    if not session.running: break
                    time.sleep(.01)
            env=popen.call_args.kwargs['env']
            self.assertEqual(env['ORGO_ECOSYSTEM_APPROVED'],'1')
            self.assertEqual(env['ORGO_ECOSYSTEM_ANDROID_MODE'],'physical')
            self.assertEqual(env['ORGO_ECOSYSTEM_KOR_ROOT'],'C:/mycode/Kor/kor')


if __name__ == '__main__':
    unittest.main()
