import copy
import unittest
from levels.orgo_browser import coverage_verdict


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.coverage = {'required_titles': ['required'], 'project': 'chromium'}
        self.data = {'stats': {'expected': 1, 'skipped': 0, 'unexpected': 0, 'flaky': 0},
                     'suites': [{'specs': [{'title': 'required', 'tests': [
                         {'projectName': 'chromium', 'status': 'expected'}]}]}]}

    def test_complete_report_passes(self):
        self.assertEqual(coverage_verdict(self.data, self.coverage, 0), 'PASS')

    def test_wrong_title_with_same_count_cannot_pass(self):
        self.data['suites'][0]['specs'][0]['title'] = 'unrelated'
        self.assertEqual(coverage_verdict(self.data, self.coverage, 0), 'PARTIAL')

    def test_empty_report_cannot_pass(self):
        self.assertEqual(coverage_verdict({}, self.coverage, 0), 'PARTIAL')

    def test_skips_flakiness_and_nonzero_exit_cannot_pass(self):
        for field in ('skipped', 'flaky'):
            data = copy.deepcopy(self.data)
            data['stats'][field] = 1
            self.assertEqual(coverage_verdict(data, self.coverage, 0), 'PARTIAL')
        self.assertEqual(coverage_verdict(self.data, self.coverage, 1), 'FAIL')

    def test_unexpected_errors_fail(self):
        self.data['errors'] = [{'message': 'setup failed'}]
        self.assertEqual(coverage_verdict(self.data, self.coverage, 0), 'FAIL')
