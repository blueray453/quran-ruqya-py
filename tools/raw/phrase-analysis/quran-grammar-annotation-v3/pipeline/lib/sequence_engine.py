"""Repeated-sequence engine shared by queries.py and generate_sequences.py.

Same definitions as the original phrase analysis (quran-phrases.csv), applied to grammatical labels:
  * a unit is n >= 1 consecutive labels (one label per complete written word) inside ONE sentence,
    never crossing a sentence boundary;
  * a unit is kept when it occurs at least `min_count` (2) times;
  * an occurrence at start i (length n) is NOT stand-alone when a repeated (n+1)-unit starts at i or at i-1,
    so  total = stand_alone + inside_longer;
  * greedy learning order: repeatedly take the unit with the best (newly covered word positions / length),
    counting each word position once.
"""
import collections
import heapq


def find_repeated(seqs, min_count=2):
    """seqs: list of label lists (one per sentence). Returns (units, toks, end).

    unit = {'length', 'labels' (tuple), 'starts' (ascending global positions), 'alone' (parallel bools)}
    Units are sorted like the original: most frequent first, then longer first, then by labels.
    """
    toks, end = [], []
    for s in seqs:
        base = len(toks)
        toks.extend(s)
        end.extend([base + len(s) - 1] * len(s))
    ids = {}
    tid = [ids.setdefault(t, len(ids)) for t in toks]
    first = collections.defaultdict(list)
    for i, t in enumerate(tid):
        first[t].append(i)
    level = [v for v in first.values() if len(v) >= min_count]
    units, n = [], 1
    while level:
        nxt = collections.defaultdict(list)
        for gi, starts in enumerate(level):
            for i in starts:
                if i + n <= end[i]:
                    nxt[(gi, tid[i + n])].append(i)
        nxt_lists = [v for v in nxt.values() if len(v) >= min_count]
        nxt_starts = {i for v in nxt_lists for i in v}
        for starts in level:
            alone = [(i not in nxt_starts and (i - 1) not in nxt_starts) for i in starts]
            units.append({'length': n, 'labels': tuple(toks[starts[0]:starts[0] + n]), 'starts': starts, 'alone': alone})
        level, n = nxt_lists, n + 1
    units.sort(key=lambda u: (-len(u['starts']), -u['length'], u['labels']))
    return units, toks, end


def coverage_by_min_length(units, total_positions, lengths=(1, 2, 3, 4, 5, 6, 8, 10)):
    """Share of word positions inside at least one repeated unit of length >= L (a repeated unit of length > L
    contains a repeated unit of length L, so marking units of exactly length L is enough)."""
    out = {}
    for L in lengths:
        cov = bytearray(total_positions)
        any_unit = False
        for u in units:
            if u['length'] == L:
                any_unit = True
                for i in u['starts']:
                    cov[i:i + L] = b'\x01' * L
        if any_unit:
            out[L] = sum(cov) / total_positions
    return out


def greedy(units, min_len=1):
    """Lazy greedy cover (identical to the original analyze.py). Returns [(unit index, new, cumulative, cost)].
    Ties are broken by unit index, i.e. by the original ordering (most frequent first)."""
    idxs = [j for j, u in enumerate(units) if u['length'] >= min_len]
    total = (max(max(u['starts']) + u['length'] for u in units) if units else 0)
    cand = {j: (units[j]['length'],
                sorted({s + k for s in units[j]['starts'] for k in range(units[j]['length'])})) for j in idxs}
    cov = bytearray(total)
    gain = lambda j: sum(1 for p in cand[j][1] if not cov[p])
    heap = [(-gain(j) / cand[j][0], j) for j in idxs]
    heapq.heapify(heap)
    sel, cum, cost = [], 0, 0
    while heap:
        _, j = heapq.heappop(heap)
        gn = gain(j)
        if gn == 0:
            continue
        eff = gn / cand[j][0]
        if heap and eff < -heap[0][0] - 1e-12:
            heapq.heappush(heap, (-eff, j))
            continue
        for p in cand[j][1]:
            cov[p] = 1
        cum += gn
        cost += cand[j][0]
        sel.append((j, gn, cum, cost))
    return sel
