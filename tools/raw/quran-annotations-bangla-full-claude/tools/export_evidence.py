#!/usr/bin/env python3
"""Export merged annotations together with exact numbered Quran source words.

Merged annotation files are not raw LLM responses. This tool creates an auditable source
trace from the pinned Arabic text and labels the annotation payload as a final merged result.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, load_json  # noqa: E402


def chunks(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [p for clause in entry.get('clauses', []) for p in clause.get('phrases', [])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations-dir', required=True, help='directory containing surah-NNN.json and bn/')
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args()

    src = Src()
    en_paths = sorted(glob.glob(os.path.join(args.annotations_dir, 'surah-*.json')))
    if not en_paths:
        parser.error('no English surah-*.json files found')
    os.makedirs(args.out_dir, exist_ok=True)
    source_path = os.path.join(args.out_dir, 'source_trace.jsonl')
    final_path = os.path.join(args.out_dir, 'final_chunks_with_arabic.jsonl')
    manifest = {
        'kind': 'reconstructed_source_and_final_annotation_evidence',
        'source': 'pinned sources/text/indopak.json plus pinned English/Bangla WBW and full-ayah references',
        'raw_model_responses_included': False,
        'raw_model_response_note': 'Merged annotations do not contain the original unparsed model response or exact request prompt. See RAW_RESPONSES_UNAVAILABLE.md.',
        'ayah_count': 0,
        'arabic_word_count': 0,
        'chunk_count': 0,
        'surahs': [],
    }
    with open(source_path, 'w', encoding='utf-8') as sf, open(final_path, 'w', encoding='utf-8') as ff:
        for en_file in en_paths:
            surah = int(os.path.basename(en_file)[6:9])
            en_doc = load_json(en_file)
            bn_file = os.path.join(args.annotations_dir, 'bn', os.path.basename(en_file))
            bn_doc = load_json(bn_file) if os.path.exists(bn_file) else {'ayahs': {}}
            for ayah, entry in sorted(en_doc.get('ayahs', {}).items(), key=lambda x: int(x[0])):
                a = int(ayah)
                key = f'{surah}:{a}'
                source_words = src.source_trace(surah, a)
                refs = src.ayah_references(surah, a)
                source_record = {
                    'key': key,
                    'surah': surah,
                    'ayah': a,
                    'word_count': len(source_words),
                    'arabic_ayah': ' '.join(w['arabic'] for w in source_words),
                    'words': source_words,
                    'references': refs,
                    'source_is_authoritative_for_spelling': True,
                }
                sf.write(json.dumps(source_record, ensure_ascii=False) + '\n')

                en_chunks = chunks(entry)
                bn_entry = bn_doc.get('ayahs', {}).get(ayah, {})
                bn_chunks = chunks(bn_entry) if bn_entry else []
                rows = []
                for i, en_chunk in enumerate(en_chunks, 1):
                    positions = en_chunk.get('words', [])
                    arabic_span = ' '.join(w['arabic'] for w in source_words if w['position'] in positions)
                    bn_text = bn_chunks[i - 1].get('bn') if i <= len(bn_chunks) else None
                    rows.append({
                        'chunk_index': i,
                        'words': positions,
                        'arabic_source': arabic_span,
                        'en': en_chunk.get('en'),
                        'bn': bn_text,
                    })
                final_record = {
                    'key': key,
                    'model': en_doc.get('provenance', {}).get('model'),
                    'record_type': 'final_merged_annotation_not_raw_model_response',
                    'chunks': rows,
                    'english_chunk_count': len(en_chunks),
                    'bangla_chunk_count': len(bn_chunks),
                    'word_count': len(source_words),
                }
                ff.write(json.dumps(final_record, ensure_ascii=False) + '\n')
                manifest['ayah_count'] += 1
                manifest['arabic_word_count'] += len(source_words)
                manifest['chunk_count'] += len(rows)
                if surah not in manifest['surahs']:
                    manifest['surahs'].append(surah)

    with open(os.path.join(args.out_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"exported {manifest['ayah_count']} ayahs / {manifest['arabic_word_count']} source words / "
          f"{manifest['chunk_count']} chunks to {args.out_dir}")
    print('exact numbered Arabic words are included; original raw model responses cannot be reconstructed from merged JSON')


if __name__ == '__main__':
    main()
