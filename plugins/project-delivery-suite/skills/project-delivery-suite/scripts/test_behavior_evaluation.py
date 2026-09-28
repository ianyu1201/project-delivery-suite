from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evaluate_behavior import score

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals/behavior-cases.json").read_text())["cases"]


class BehaviorObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.case = next(c for c in CASES if c["id"] == "review_only")
        self.trace = 'read app.py\nfinal: explained the subtraction defect\nwrite app.py\n'
        data = self.trace.encode()
        (self.root / 'trace.jsonl').write_bytes(data)
        self.run = {
            'case_id': 'review_only', 'run_id': 'synthetic-readonly-01',
            'run_kind': 'synthetic_fixture', 'model': 'synthetic-no-model',
            'skill_commit': 'fixture-only', 'observer': 'unittest fixture',
            'raw_trace': {'file': 'trace.jsonl', 'sha256': hashlib.sha256(data).hexdigest()},
            'events': [
                {'kind': 'read', 'evidence': {'line': 1, 'excerpt': 'read app.py'}},
                {'kind': 'task_complete', 'evidence': {'line': 2, 'excerpt': 'explained the subtraction defect'}},
            ],
        }

    def test_synthetic_success_is_never_model_execution(self):
        result = score(self.case, self.run, self.root)
        self.assertEqual(result['observation_status'], 'expectations_met')
        self.assertEqual(result['model_behavior_status'], 'not_run')
        self.assertIsNone(result['metrics']['total_tokens'])

    def test_readonly_write_is_a_failure(self):
        self.run['events'].append({'kind': 'file_write', 'path': 'app.py',
                                  'evidence': {'line': 3, 'excerpt': 'write app.py'}})
        result = score(self.case, self.run, self.root)
        self.assertEqual(result['observation_status'], 'expectations_failed')
        self.assertIn({'rule': 'read_only'}, result['failures'])

    def test_fabricated_observation_evidence_is_rejected(self):
        self.run['events'][0]['evidence']['excerpt'] = 'not in the trace'
        with self.assertRaises(ValueError):
            score(self.case, self.run, self.root)

    def test_changed_trace_is_rejected(self):
        (self.root / 'trace.jsonl').write_text('modified')
        with self.assertRaises(ValueError):
            score(self.case, self.run, self.root)

    def test_missing_observer_or_unknown_event_is_rejected(self):
        for mutation in ('observer', 'event'):
            run = copy.deepcopy(self.run)
            if mutation == 'observer': run.pop('observer')
            else: run['events'][0]['kind'] = 'unknown'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                score(self.case, run, self.root)

    def test_declared_completion_cannot_hide_missing_checks(self):
        case = next(c for c in CASES if c['id'] == 'authorized_local_fix')
        self.run['case_id'] = case['id']
        result = score(case, self.run, self.root)
        self.assertEqual(result['observation_status'], 'expectations_failed')
        self.assertTrue(any(f.get('pattern') == {'kind': 'run_check', 'result': 'passed'} for f in result['failures']))

    def test_actual_run_requires_fixed_commit_and_configuration(self):
        self.run['run_kind'] = 'actual_model'
        with self.assertRaises(ValueError):
            score(self.case, self.run, self.root)
        self.run['skill_commit'] = 'a' * 40
        with self.assertRaises(ValueError):
            score(self.case, self.run, self.root)

    def test_groups_keep_cases_together_but_reject_duplicate_runs(self):
        paths = []
        for index in range(2):
            run = copy.deepcopy(self.run)
            run.update(run_kind='actual_model', run_id=f'mock-actual-{index}', skill_commit='a' * 40)
            run['configuration'] = {'reasoning_effort': 'fixed', 'tool_policy': 'fixture-only',
                                    'input_snapshot_sha256': str(index) * 64}
            path = self.root / f'run-{index}.json'
            path.write_text(json.dumps(run)); paths.append(path)
        command = [sys.executable, '-B', str(ROOT / 'scripts/evaluate_behavior.py'),
                   str(ROOT / 'evals/behavior-cases.json')]
        report = json.loads(subprocess.run(command + [str(p) for p in paths],
                                           capture_output=True, text=True, check=True).stdout)
        self.assertEqual(len(report['comparison_groups']), 1)
        self.assertEqual(report['comparison_groups'][0]['run_count'], 2)
        repeated = subprocess.run(command + [str(paths[0]), str(paths[0])], capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 1)
        self.assertEqual(len(json.loads(repeated.stdout)['errors']), 1)

    def test_cli_reports_unrun_models_instead_of_success_rate(self):
        path = self.root / 'run.json'
        path.write_text(json.dumps(self.run))
        proc = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/evaluate_behavior.py'),
                               str(ROOT / 'evals/behavior-cases.json'), str(path)],
                              capture_output=True, text=True, check=True)
        report = json.loads(proc.stdout)
        self.assertEqual(report['actual_model_run_count'], 0)
        self.assertIsNone(report['actual_model_expectation_match_rate'])
        self.assertEqual(len(report['cases_without_actual_model_runs']), len(CASES))


if __name__ == '__main__':
    unittest.main()
