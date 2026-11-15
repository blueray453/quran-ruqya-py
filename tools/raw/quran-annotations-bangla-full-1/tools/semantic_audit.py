#!/usr/bin/env python3
"""Optional second-pass semantic/syntactic audit of already-fixed Arabic chunk spans.

This tool does not rewrite translations or boundaries. It asks an OpenRouter model to identify
candidate omissions, borrowed/duplicated meaning, broken Arabic dependencies, and terminology
violations. Every full prompt and raw answer is saved under <out-dir>/attempts/.
"""
import argparse
import json
import os
import re
import sys
import time
import uuid
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, load_json, terminology_flags  # noqa: E402

API = 'https://openrouter.ai/api/v1/chat/completions'

SYSTEM = """You are a careful Quranic Arabic phrase-alignment reviewer.
Audit the supplied final chunk annotations against the exact numbered Arabic source words.
Do not rewrite, resegment, or silently repair the annotations. Return review findings only.

The target is the smallest VALID local Arabic syntactic-semantic unit, not the smallest possible
word count. Flag a split only when it breaks a necessary local dependency or makes one of the
fragments misleading. Elliptical fragments are allowed when their meaning is correctly aligned.
Do not demand that each fragment be a complete English or Bangla sentence.

For each chunk, check whether its English and Bangla fragments convey all and only the meaning
of the Arabic words assigned to that chunk. Check for meaning moved to a neighbour, duplicated,
missing, or incorrectly added. Check nearby boundaries for stranded particles, auxiliaries,
subjects, predicates, complements, or conditional constructions. Do not use word-count averages
as a quality target. Do not assume an English/Bangla reference translation is authoritative for
chunk boundaries; use it only as context.

Terminology is mandatory: never use God/gods/Lord/lords/lordship/deity/deities. Use Allah for الله,
Rabb for رَبّ, and ilah/ilahs for إِلٰه / آلِهَة. In Bangla use আল্লাহ / রব / ইলাহ; never ঈশ্বর,
প্রভু, or খোদা. Apply terminology according to the actual Arabic wording.

Return exactly one JSON object:
{"issues":[{"category":"meaning_omission|meaning_borrowing_or_duplication|syntactic_dependency|translation_mistranslation|terminology|bangla_alignment","severity":"high|medium|low","chunk_indices":[1],"explanation":"...","suggested_action":"..."}]}
Use an empty issues array when you find no issue. Do not invent issues just because a fragment is elliptical.
"""


def chunks(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [p for clause in entry.get('clauses', []) for p in clause.get('phrases', [])]


def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    decoder = json.JSONDecoder()
    for i, char in enumerate(text):
        if char == '{':
            try:
                obj, _ = decoder.raw_decode(text, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
    raise ValueError('model response did not contain valid JSON object')


def make_user(src, surah, ayah, en_entry, bn_entry):
    source_words = src.source_trace(surah, ayah)
    en_chunks = chunks(en_entry)
    bn_chunks = chunks(bn_entry) if bn_entry else []
    lines = [f'Ayah: {surah}:{ayah}', 'Exact Arabic source words:']
    for word in source_words:
        lines.append(f"{word['position']}. {word['arabic']} — EN word gloss: {word['en_wbw']} — BN word gloss: {word['bn_wbw']}")
    lines.append('\nFinal chunks (spans are fixed for this audit):')
    for i, chunk in enumerate(en_chunks, 1):
        positions = chunk.get('words', [])
        arabic = ' '.join(w['arabic'] for w in source_words if w['position'] in positions)
        bn = bn_chunks[i - 1].get('bn') if i <= len(bn_chunks) else '[missing Bangla overlay]'
        lines.append(f"Chunk {i}; source positions {positions}; Arabic: {arabic}")
        lines.append(f"  English: {chunk.get('en', '')}")
        lines.append(f"  Bangla: {bn}")
    refs = src.ayah_references(surah, ayah)
    lines.append('\nReference translations (context only, not segmentation authority):')
    lines.append('English: ' + str(refs.get('en_reference') or '[not available]'))
    lines.append('Bangla: ' + str(refs.get('bn_reference') or '[not available]'))
    return '\n'.join(lines)


def call_model(model, system, user, max_tokens):
    body = {
        'model': model,
        'temperature': 0,
        'max_tokens': max_tokens,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'usage': {'include': True},
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            'Content-Type': 'application/json',
            'X-Title': 'quran-chunk-semantic-audit',
        },
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        payload = json.loads(response.read().decode('utf-8'))
    if 'error' in payload:
        raise RuntimeError(json.dumps(payload['error'], ensure_ascii=False))
    message = payload['choices'][0]['message']
    text = message.get('content') or ''
    if not text.strip():
        raise RuntimeError('empty semantic audit response')
    return text, payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--annotations-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--model', default='openai/gpt-6-luna')
    ap.add_argument('--ayahs', default='', help='optional comma list e.g. 2:196,2:282,67:7-11')
    ap.add_argument('--max-tokens', type=int, default=3500)
    args = ap.parse_args()

    if not os.environ.get('OPENROUTER_API_KEY'):
        ap.error('set OPENROUTER_API_KEY before running the live semantic audit')

    src = Src()
    allowed = None
    if args.ayahs.strip():
        from run_llm import parse_spec
        allowed = set(parse_spec(args.ayahs.split(','), src))

    os.makedirs(os.path.join(args.out_dir, 'attempts'), exist_ok=True)
    results = []
    summary_path = os.path.join(args.out_dir, 'semantic_audit.json')
    for path in sorted(__import__('glob').glob(os.path.join(args.annotations_dir, 'surah-*.json'))):
        surah = int(os.path.basename(path)[6:9])
        en_doc = load_json(path)
        bn_path = os.path.join(args.annotations_dir, 'bn', os.path.basename(path))
        bn_doc = load_json(bn_path) if os.path.exists(bn_path) else {'ayahs': {}}
        for ayah, en_entry in sorted(en_doc.get('ayahs', {}).items(), key=lambda x: int(x[0])):
            a = int(ayah)
            if allowed is not None and (surah, a) not in allowed:
                continue
            key = f'{surah}:{a}'
            user = make_user(src, surah, a, en_entry, bn_doc.get('ayahs', {}).get(ayah))
            attempt_id = uuid.uuid4().hex
            started = time.time()
            attempt = {
                'attempt_id': attempt_id,
                'kind': 'semantic_syntactic_audit',
                'ayah': key,
                'model': args.model,
                'temperature': 0,
                'request': {'endpoint': API, 'system_prompt': SYSTEM, 'user_prompt': user,
                            'max_tokens': args.max_tokens},
            }
            try:
                text, payload = call_model(args.model, SYSTEM, user, args.max_tokens)
                parsed = parse_json(text)
                local_terms = []
                for i, chunk in enumerate(chunks(en_entry), 1):
                    for issue in terminology_flags(chunk.get('en', ''), None):
                        local_terms.append({'chunk_indices': [i], 'category': 'terminology',
                                            'severity': 'high', 'explanation': issue,
                                            'suggested_action': 'replace with the Arabic-grounded Islamic term'})
                for i, chunk in enumerate(chunks(bn_doc.get('ayahs', {}).get(ayah, {})), 1):
                    for issue in terminology_flags('', chunk.get('bn', '')):
                        local_terms.append({'chunk_indices': [i], 'category': 'terminology',
                                            'severity': 'high', 'explanation': issue,
                                            'suggested_action': 'replace with আল্লাহ / রব / ইলাহ according to Arabic'})
                issues = parsed.get('issues', []) if isinstance(parsed.get('issues'), list) else []
                issues.extend(local_terms)
                attempt.update({
                    'duration_seconds': round(time.time() - started, 2),
                    'usage': payload.get('usage'),
                    'raw_model_text': text,
                    'provider_response': payload,
                    'parsed_result': parsed,
                    'status': 'complete',
                })
                result = {'ayah': key, 'model': args.model, 'status': 'complete', 'issues': issues,
                          'attempt_id': attempt_id}
            except Exception as exc:
                attempt.update({'duration_seconds': round(time.time() - started, 2), 'error': str(exc),
                                'status': 'error'})
                result = {'ayah': key, 'model': args.model, 'status': 'error', 'error': str(exc),
                          'attempt_id': attempt_id}
            with open(os.path.join(args.out_dir, 'attempts', f'{attempt_id}.json'), 'w', encoding='utf-8') as fh:
                json.dump(attempt, fh, ensure_ascii=False, indent=2)
            results.append(result)
            with open(summary_path, 'w', encoding='utf-8') as fh:
                json.dump({'model': args.model, 'annotations_dir': os.path.abspath(args.annotations_dir),
                           'results': results}, fh, ensure_ascii=False, indent=2)
            print(f"{key}: {result['status']} — {len(result.get('issues', []))} issue(s)")

    print(f'Wrote audit report: {summary_path}')
    print('This is a review aid only; it does not modify any annotation.')


if __name__ == '__main__':
    main()
