#!/usr/bin/env python3
"""Fail-fast checks for expected output populations from the bundled source snapshot."""
import argparse, csv, json
from pathlib import Path


def readcsv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def check_eq(actual, expected, label):
    if actual != expected:
        raise SystemExit(f'VALIDATION FAILED: {label}: expected {expected}, found {actual}')
    print(f'OK  {label}: {actual}')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--csv-dir',required=True); a=ap.parse_args(); c=Path(a.csv_dir)
    f=json.loads((c/'frequency_build_summary.json').read_text(encoding='utf-8'))
    i=json.loads((c/'summary.json').read_text(encoding='utf-8'))
    check_eq(f['qul']['surface_tokens'],77432,'QUL surface word tokens')
    check_eq(f['qul']['surface_types'],21294,'QUL distinct surface forms')
    mapped={r[0]:r[1] for r in f['qul']['mapping']}
    check_eq(mapped['lemma'],72510,'QUL lemma mapped occurrences')
    check_eq(mapped['stem'],77427,'QUL stem mapped occurrences')
    check_eq(mapped['root'],50298,'QUL root mapped occurrences')
    check_eq(f['qac_morphology']['qac_stem_rows'],77915,'QAC morphology STEM rows')
    check_eq(f['qac_morphology']['qac_verb_stems'],19356,'QAC verb STEM rows')
    check_eq(f['qac_morphology']['imperfect_verb_stems'],8330,'QAC imperfect verb STEM rows')
    check_eq(f['qac_syntax']['qac_csv_rows'],139376,'QAC convenience CSV rows')
    check_eq(f['qac_syntax']['qac_relation_instances'],103781,'QAC observed dependency relation rows')
    check_eq(f['qac_syntax']['qac_constituent_annotation_rows'],26463,'QAC constituent annotation rows')
    check_eq(f['masaq']['masaq_rows'],157676,'Supplied MASAQ CSV rows')
    check_eq(f['masaq']['masaq_roles_observed'],110886,'MASAQ observed word/segment role rows')
    check_eq(f['masaq']['masaq_unique_word_positions'],77411,'MASAQ unique word positions')
    q=i['qac_v0_4']; m=i['masaq_archive_csv']
    check_eq(q['broad_ism_stem_rows'],40778,'QAC broad Ism STEM rows')
    check_eq(q['broad_ism_unique_words'],40773,'QAC broad Ism unique word positions')
    check_eq(q['gender'].get('M'),26090,'QAC Ism masculine annotations')
    check_eq(q['gender'].get('F'),6026,'QAC Ism feminine annotations')
    check_eq(q['gender'].get('UNMARKED'),8662,'QAC Ism unmarked gender annotations')
    check_eq(q['number'].get('P'),9692,'QAC Ism plural annotations')
    check_eq(q['number'].get('S'),6593,'QAC Ism singular annotations')
    check_eq(q['number'].get('D'),269,'QAC Ism dual annotations')
    check_eq(q['number'].get('UNMARKED'),24224,'QAC Ism unmarked number annotations')
    check_eq(q['case'].get('GEN'),12610,'QAC Ism genitive annotations')
    check_eq(q['case'].get('ACC'),10331,'QAC Ism accusative annotations')
    check_eq(q['case'].get('NOM'),8941,'QAC Ism nominative annotations')
    check_eq(m['ism_stem_rows'],39237,'MASAQ Ism-family STEM rows')
    # Ensure all expected report inputs are present.
    for name in ['10_traditional_grammar_architecture.csv','11_ism_four_properties_complete_taxonomy.csv',
                 '13_phrase_construction_taxonomy.csv','14_phrase_function_taxonomy_masaq.csv',
                 'vocabulary_surface_frequency.csv','sarf_verb_form_frequency.csv',
                 '24_qac_ism_gender_distribution.csv','27_qac_ism_definiteness_evidence_distribution.csv',
                 '15_available_source_phrase_span_frequency.csv','01d_masaq_word_role_frequency_not_phrase_function.csv']:
        if not (c/name).exists(): raise SystemExit(f'VALIDATION FAILED: missing output {name}')
    print('OK  Required report input files present')
    print('All snapshot validation checks passed.')

if __name__=='__main__': main()
