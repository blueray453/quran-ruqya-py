"""Q20  Which irregularities does the source data contain, and exactly which words/sentences are affected?

Usage: python3 queries/q20_source_issues.py
These are COMPLETE lists (the files in docs/examples/ show one example each).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which words and sentences are irregular in the source (merged, split, fragment, re-tagged)?'
KIND = 'original'
LIMITS = 'Lists what the validation found; nothing is corrected silently.'
ARGS = [('full', 'print the complete lists, not just the counts (0/1)', 0)]
DEMO = {}


def CHECK(a):
    c = a['counts']
    return (c['merged_treebank_words'], c['words_split_across_sentences'], c['prefix_only_fragment_sentences'],
            c['sentences_crossing_ayah'], c['words_absent_in_treebank']) == (3, 41, 26, 836, 0)


def answer(full=0):
    L = G.source_issue_lists()
    out = {'counts': {k: len(v) for k, v in L.items()}}
    if int(full):
        out['lists'] = L
    return out


if __name__ == '__main__':
    run(sys.modules[__name__])
