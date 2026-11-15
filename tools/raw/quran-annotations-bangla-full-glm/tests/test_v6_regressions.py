import json
import pathlib
import re
import sys
import unittest
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ayahlib import Src, normalise, syntactic_review_flags, terminology_flags  # noqa: E402


class V6RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = Src()

    def test_source_trace_recovers_exact_numbered_arabic_words(self):
        trace = self.src.source_trace(2, 196)
        self.assertEqual(len(trace), self.src.n_words(2, 196))
        selected = [trace[i - 1]['arabic'] for i in (61, 62, 63)]
        self.assertEqual(selected, ['لَّمۡ', 'يَكُنۡ', 'اَهۡلُهٗ'])

    def test_english_forbidden_terms_are_rejected(self):
        n = self.src.n_words(2, 255)
        for word in ('God', 'gods', 'Lord', 'lordship', 'deity'):
            errs, _ = normalise([{'words': [1, n], 'en': f'The {word}', 'bn': 'আল্লাহ'}], n)
            self.assertTrue(any('prohibited generic religious term' in e for e in errs), word)

    def test_bangla_forbidden_terms_are_rejected(self):
        for term in ('ঈশ্বর', 'প্রভু', 'খোদা'):
            issues = terminology_flags('Allah', f'{term}')
            self.assertTrue(issues, term)

    def test_islamic_terms_are_allowed(self):
        for english in ('Allah', 'our Rabb', 'there is no ilah'):
            self.assertEqual(terminology_flags(english, 'আল্লাহ, রব, ইলাহ'), [])

    def test_standalone_dependent_word_is_reviewed(self):
        flags = syntactic_review_flags([
            {'words': [3], 'en': 'if'},
            {'words': [4, 5], 'en': 'your water becomes'},
            {'words': [6], 'en': 'sunken'},
        ])
        self.assertTrue(any('standalone dependent/function word' in f for f in flags))
        self.assertTrue(any('linking verb' in f for f in flags))

    def test_pilot_regression_fixture_is_source_grounded(self):
        fixture = json.loads((ROOT / 'tests/regression_cases.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(fixture['cases']), 8)
        for case in fixture['cases']:
            surah, ayah = map(int, case['ayah'].split(':'))
            trace = self.src.source_trace(surah, ayah)
            for pos in case['source_words']:
                self.assertGreaterEqual(pos, 1)
                self.assertLessEqual(pos, len(trace))

    def test_historical_retry_ledger_keeps_raw_payload_limit_explicit(self):
        events = [json.loads(line) for line in
                  (ROOT / 'pilot_evidence/historical_retry_events.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(events), 4)
        self.assertTrue(all(e['status'] == 'resolved' for e in events))
        self.assertTrue(all(e['initial_raw_response_available'] is False for e in events))
        self.assertEqual({e['ayah'] for e in events}, {'67:30', '2:233', '4:12', '24:31'})

    def test_source_linked_pilot_evidence_has_all_45_ayahs(self):
        manifest = json.loads((ROOT / 'pilot_evidence/source_linked/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['ayah_count'], 45)
        self.assertEqual(manifest['arabic_word_count'], 1208)
        source_lines = (ROOT / 'pilot_evidence/source_linked/source_trace.jsonl').read_text(encoding='utf-8').splitlines()
        chunk_lines = (ROOT / 'pilot_evidence/source_linked/final_chunks_with_arabic.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(source_lines), 45)
        self.assertEqual(len(chunk_lines), 45)
        for line in chunk_lines:
            record = json.loads(line)
            self.assertTrue(all(c['arabic_source'] for c in record['chunks']))

    def test_live_runner_archives_invalid_response_and_successful_retry(self):
        tag = 'test_retry_archive'
        run_dir = ROOT / 'runs' / tag
        shutil.rmtree(run_dir, ignore_errors=True)
        try:
            subprocess.run([
                sys.executable, 'tools/run_llm.py', '--ayahs', '67:1', '--tag', tag,
                '--mock-replay', '--mock-invalid-once', '--workers', '1', '--retries', '1',
                '--coarse-retries', '0', '--no-merge',
            ], cwd=ROOT, check=True, capture_output=True, text=True)
            events = [json.loads(line) for line in (run_dir / 'retry_events.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]['event'], 'invalid_model_response')
            self.assertEqual(events[1]['event'], 'invalid_response_resolved_by_retry')
            self.assertEqual(events[1]['status'], 'resolved')
            original = json.loads((run_dir / events[0]['attempt_file']).read_text(encoding='utf-8'))
            resolving = json.loads((run_dir / events[1]['resolving_attempt_file']).read_text(encoding='utf-8'))
            self.assertIn('raw_model_text', original)
            self.assertIn('system_prompt', original['request'])
            self.assertIn('user_prompt', original['request'])
            self.assertIn('raw_model_text', resolving)
            final_raw = json.loads((run_dir / 'raw/067-001.json').read_text(encoding='utf-8'))
            self.assertEqual(final_raw['source']['word_count'], 9)
            self.assertEqual(final_raw['final_attempt_id'], resolving['attempt_id'])
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def test_pilot_evidence_contains_no_disallowed_terms(self):
        base = ROOT / 'pilot_evidence/final_annotations'
        forbidden_en = re.compile(r'\b(?:god|gods|lord|lords|lordship|deity|deities)\b', re.I)
        forbidden_bn = re.compile(r'ঈশ্বর|প্রভু|খোদা')
        for path in base.glob('surah-*.json'):
            doc = json.loads(path.read_text(encoding='utf-8'))
            for ayah in doc['ayahs'].values():
                for chunk in ayah['chunks']:
                    self.assertIsNone(forbidden_en.search(chunk.get('en', '')), f'{path}: {chunk}')
        for path in (base / 'bn').glob('surah-*.json'):
            doc = json.loads(path.read_text(encoding='utf-8'))
            for ayah in doc['ayahs'].values():
                for chunk in ayah['chunks']:
                    self.assertIsNone(forbidden_bn.search(chunk.get('bn', '')), f'{path}: {chunk}')


if __name__ == '__main__':
    unittest.main()
