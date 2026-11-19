#!/usr/bin/env python3
"""Write small, human-readable slices of the generated layers to docs/examples/ (for reading the schema)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import queries as q

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'examples')


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print('wrote docs/examples/' + name)


W, S = q.load()
words, sents = W['words'], S['sentences']
dump('ayah-67-15.json', {
    'note': 'Word layer records for 67:15:1-6 and the sentence layer record they belong to (sentence 10846).',
    'words': {k: words[k] for k in ['67:15:%d' % i for i in range(1, 7)]},
    'sentence': sents['10846']})
dump('word-split-across-sentences.json', {
    'note': 'Word 9:100:1: its prefixes are annotated in sentence 3944, its stem in sentence 3945. The word is assigned to 3945; '
            'sentence 3944 is a prefix-only fragment and owns no written word.',
    'word': words['9:100:1'], 'sentence_3944_fragment': sents['3944']})
dump('word-absent-in-treebank.json', {
    'note': 'Word 2:181:14 exists in the WBW file but has no Treebank annotation; it keeps a record with no segments.',
    'word': words['2:181:14']})
small = min((s for s in sents.values() if s['span']['crosses_ayah'] and len(s['nodes']) < 40), key=lambda s: len(s['nodes']))
dump('sentence-crossing-ayah.json', {'note': 'A sentence whose words lie in more than one ayah.', 'sentence': small})
