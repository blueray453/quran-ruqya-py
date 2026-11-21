"""Q11  How are the words connected through syntactic relationships? (dependency tree of a sentence)

Usage: python3 queries/q11_dependency_tree.py 10846
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'How are the words connected through syntactic relationships?'
KIND = 'original'
LIMITS = 'The tree is the Treebank\'s head-dependent structure at segment level; NonRel prefixes are listed apart because they point to themselves.'
ARGS = [('sentence', 'sentence id', ...)]
DEMO = {'sentence': '10846'}
CHECK = lambda a: len(a['tree']) >= 8 and a['tree'][0].startswith('[root]')


def answer(sentence):
    s = sentences()[str(sentence)]
    nodes = s['nodes']
    kids = collections.defaultdict(list)
    for n in nodes:
        if n['head'] != n['token_id']:
            kids[n['head']].append(n)

    def label(n):
        if n['implicit']:
            return '%s (implicit) %s' % (n['morphology']['text_uthmani'], node_pos(n))
        sg = next(g for g in words()[n['word']]['segments'] if g['location'] == n['segment'])
        return '%s %s' % (sg['text_uthmani'], node_pos(n))

    lines, seen = [], set()

    def walk(n, depth):
        if n['token_id'] in seen:
            return
        seen.add(n['token_id'])
        lines.append('%s[%s] %s  #%d' % ('    ' * depth, n['rel'], label(n), n['token_id']))
        for c in kids[n['token_id']]:
            walk(c, depth + 1)
    for n in nodes:
        if n['head'] == n['token_id'] and n['rel'] != 'NonRel':
            walk(n, 0)
    loose = [label(n) + ' #%d' % n['token_id'] for n in nodes if n['token_id'] not in seen]
    return {'sentence_id': int(sentence), 'tree': lines, 'not_attached_in_tree': loose}


if __name__ == '__main__':
    run(sys.modules[__name__])
