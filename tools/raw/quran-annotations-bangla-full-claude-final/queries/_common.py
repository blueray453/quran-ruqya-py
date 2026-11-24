"""Shared helpers for the question scripts (queries/qNN_*.py).

Every query module defines:
  QUESTION  the question it answers          KIND    original | derived | partial | research
  LIMITS    what the data cannot tell you    ARGS    [(name, help, default)]   default ... = required positional
  DEMO      example arguments                CHECK   function(answer) -> bool, a known-good answer used by _self_test.py
  answer()  returns a JSON-serialisable answer built ONLY from the two JSON layers in output/
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline', 'lib'))
import grammar_data as G                      # noqa: E402
from grammar_data import words, sentences, load, node_pos, word_text, syntax_of_word, sentence_of_word  # noqa: E402,F401


def run(mod):
    ap = argparse.ArgumentParser(description=mod.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name, help_, default in mod.ARGS:
        if default is ...:
            ap.add_argument(name, help=help_)
        else:
            ap.add_argument('--' + name, default=default, help=help_, type=type(default) if default is not None else str)
    print(json.dumps(mod.answer(**vars(ap.parse_args())), ensure_ascii=False, indent=1))


def ref(layer=0):
    return load()[layer]['reference_data']


def describe(sheet, tag):
    e = ref()['features'][sheet]['entries'].get(tag)
    return e['English Description'] if e else None


def seg_summary(s):
    return {'location': s['location'], 'type': s['type'], 'text_uthmani': s['text_uthmani'], 'pos': s['pos']}
