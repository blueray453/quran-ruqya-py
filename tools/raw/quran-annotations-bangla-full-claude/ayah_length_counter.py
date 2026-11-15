import sys, collections

sys.path.insert(0, 'tools')
from ayahlib import *
from chunker_report import load_chunks

src = Src()
toks, ends = load_chunks()
bands = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90), (91, 100),
         (101, 110), (111, 120), (121, 130)]

def band(n):
    for lo, hi in bands:
        if lo <= n <= hi: return (lo, hi)

tot = collections.Counter()
wd = collections.Counter()
cov = collections.Counter()
for (s, a) in src.maxkey:
    n = src.n_words(s, a)
    b = band(n)
    tot[b] += 1
    wd[b] += n
    if (s, a) in toks: cov[b] += 1
print('band (words)   ayahs   share-of-words   chunker-covered ayahs')
for b in bands:
    print(f'{b[0]:>3}-{b[1] if b[1]<999 else "+":<4}      {tot[b]:5d}   {wd[b]/77432:6.1%}          {cov[b]}')
