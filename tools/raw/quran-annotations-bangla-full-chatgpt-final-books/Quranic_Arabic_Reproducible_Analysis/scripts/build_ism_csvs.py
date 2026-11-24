import csv, re, json, math, zipfile, shutil, os, argparse
from collections import Counter, defaultdict
from pathlib import Path

PARSER = argparse.ArgumentParser(description='Generate quantitative Ism feature CSVs from QAC and MASAQ source files.')
PARSER.add_argument('--grammar-dir', required=True, help='Directory containing QAC and MASAQ grammar source files')
PARSER.add_argument('--output-dir', required=True, help='Directory where Ism CSVs will be written')
ARGS = PARSER.parse_args()
BASE = Path(ARGS.grammar_dir)
OUT = Path(ARGS.output_dir)
OUT.mkdir(parents=True, exist_ok=True)
QAC_TXT = BASE / 'quranic-corpus-morphology-0.4.txt'
MASAQ_CSV = BASE / 'MASAQ.csv'

# ---------------- Helpers ----------------
def pct(n, d):
    return (100.0*n/d) if d else 0.0

def write_csv(name, headers, rows):
    p = OUT / name
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return p

def counter_rows(counter, denominator, label_name='category', count_name='frequency', pct_name='pct_of_denominator', sort=True):
    items = counter.most_common() if sort else list(counter.items())
    return [[k, v, round(pct(v, denominator), 4)] for k,v in items]

# ---------------- QAC raw morphology 0.4 ----------------
qac = []
for line in QAC_TXT.read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#') or line.startswith('LOCATION'):
        continue
    parts = line.split('\t')
    if len(parts) < 4:
        continue
    loc, form, tag, feature_str = parts[:4]
    m = re.fullmatch(r'\((\d+):(\d+):(\d+):(\d+)\)', loc)
    if not m:
        continue
    s, a, w, seg = map(int, m.groups())
    features = feature_str.split('|')
    qac.append({'sura':s, 'ayah':a, 'word':w, 'segment':seg, 'loc':loc, 'form':form,
                'tag':tag, 'features':features, 'feature_str':feature_str})

q_stems = [r for r in qac if 'STEM' in r['features']]
QAC_ISM_POS = {'N','PN','ADJ','T','LOC','PRON','REL','DEM'}
q_ism = [r for r in q_stems if r['tag'] in QAC_ISM_POS]
q_word_key = lambda r: (r['sura'],r['ayah'],r['word'])
q_ism_keys = {q_word_key(r) for r in q_ism}

# POS membership is anchored to QAC morphology v0.4. The companion Quranic.csv
# export is joined by exact segment location for its structured gender/number/case/state
# columns. This retains the QAC v0.4 40,778-row Ism denominator while using the
# companion export's complete feature columns (including compound number codes).
qcsv_path = BASE / 'Quranic.csv'
qcsv_by_loc = {}
with qcsv_path.open('r', encoding='utf-16', newline='') as f:
    for _row in csv.DictReader(f, delimiter='\t'):
        if _row.get('location') and _row['location'] != '_':
            qcsv_by_loc[_row['location']] = _row
for r in q_ism:
    x = qcsv_by_loc.get(r['loc'])
    if x is None:
        raise ValueError(f'QAC crosswalk failed for Ism location {r["loc"]}')
    r['gender'] = x.get('gender','_') if x.get('gender','_') not in ('','_') else 'UNMARKED'
    r['number'] = x.get('number','_') if x.get('number','_') not in ('','_') else 'UNMARKED'
    r['case'] = x.get('nominal_case','_') if x.get('nominal_case','_') not in ('','_') else 'UNMARKED'
    r['state'] = x.get('nominal_state','_') if x.get('nominal_state','_') not in ('','_') else 'UNMARKED'

# Include composed gender-number tags, e.g. MS/FP, or person-gender-number 3MS.
def gender_of(features):
    seen = set()
    for t in features:
        if t in ('M','F'):
            seen.add(t)
        m = re.fullmatch(r'(?:[123])?([MF])([SDP])', t)
        if m:
            seen.add(m.group(1))
    if seen == {'M'}: return 'M'
    if seen == {'F'}: return 'F'
    if seen == {'M','F'}: return 'MIXED/CONFLICT'
    return 'UNMARKED'

def number_of(features):
    seen = set()
    for t in features:
        if t in ('S','D','P'):
            seen.add(t)
        m = re.fullmatch(r'(?:[123])?[MF]([SDP])', t)
        if m:
            seen.add(m.group(1))
        m_person_number = re.fullmatch(r'[123]([SDP])', t)
        if m_person_number:
            seen.add(m_person_number.group(1))
    if len(seen)==1: return next(iter(seen))
    if len(seen)>1: return 'MIXED/CONFLICT'
    return 'UNMARKED'

def feature_presence(features, vals):
    return any(t in vals for t in features)

# Feature values above are joined from the QAC companion table by exact location.

q_pos_counts = Counter(r['tag'] for r in q_ism)
q_gender = Counter(r['gender'] for r in q_ism)
q_number = Counter(r['number'] for r in q_ism)
q_case = Counter(r['case'] for r in q_ism)
q_state = Counter(r['state'] for r in q_ism)

# by POS tables
q_gender_by_pos = defaultdict(Counter)
q_number_by_pos = defaultdict(Counter)
q_case_by_pos = defaultdict(Counter)
q_state_by_pos = defaultdict(Counter)
for r in q_ism:
    q_gender_by_pos[r['tag']][r['gender']] += 1
    q_number_by_pos[r['tag']][r['number']] += 1
    q_case_by_pos[r['tag']][r['case']] += 1
    q_state_by_pos[r['tag']][r['state']] += 1

# QAC attached article and pronoun suffixes: word-position markers.
q_article_keys = {q_word_key(r) for r in qac if r['tag']=='DET' and 'PREFIX' in r['features'] and 'Al+' in r['features']}
q_pron_suffix_keys = {q_word_key(r) for r in qac if r['tag']=='PRON' and 'SUFFIX' in r['features']}
q_indef_keys = {q_word_key(r) for r in q_ism if r['state']=='INDEF'}
q_pn_keys = {q_word_key(r) for r in q_ism if r['tag']=='PN'}
q_intrinsic_pron_keys = {q_word_key(r) for r in q_ism if r['tag'] in {'PRON','REL','DEM'}}

# On unique Ism word positions, assign one evidence class by priority.
# Explicit INDEF is kept as the corpus state even where its POS label is anomalous.
definite_class = {}
for k in q_ism_keys:
    if k in q_indef_keys:
        definite_class[k] = 'Explicit INDEF state'
    elif k in q_article_keys:
        definite_class[k] = 'Al- article prefix'
    elif k in q_intrinsic_pron_keys:
        definite_class[k] = 'Pronoun / relative / demonstrative (inherently definite)'
    elif k in q_pn_keys:
        definite_class[k] = 'Proper noun (inherently definite)'
    elif k in q_pron_suffix_keys:
        definite_class[k] = 'Attached pronoun suffix (possessive/annexed)'
    else:
        definite_class[k] = 'Definiteness not determined by available marker'
q_def_class_counts = Counter(definite_class.values())

# Conflict / overlap diagnostics on word-position sets.
q_overlaps = [
    ('Al- prefix ∩ INDEF', len(q_article_keys & q_indef_keys)),
    ('Al- prefix ∩ proper noun', len(q_article_keys & q_pn_keys)),
    ('INDEF ∩ proper noun', len(q_indef_keys & q_pn_keys)),
    ('INDEF ∩ PRON/REL/DEM', len(q_indef_keys & q_intrinsic_pron_keys)),
    ('Attached PRON suffix ∩ INDEF', len(q_pron_suffix_keys & q_indef_keys)),
    ('Attached PRON suffix ∩ Al- prefix', len(q_pron_suffix_keys & q_article_keys)),
    ('Attached PRON suffix ∩ intrinsic definite pronoun', len(q_pron_suffix_keys & q_intrinsic_pron_keys)),
    ('Attached PRON suffix ∩ proper noun', len(q_pron_suffix_keys & q_pn_keys)),
]

# Ambiguous QAC interrogative/conditional tags are preserved separately: their POS
# tagsets can refer to both Harf and Ism and need context-level curation.
q_ambiguous = [r for r in q_stems if r['tag'] in {'INTG','COND'}]
q_ambig_counter = Counter((r['tag'], next((t[4:] for t in r['features'] if t.startswith('LEM:')), 'NO_LEMMA'), r['form']) for r in q_ambiguous)
write_csv('22_qac_interrogative_conditional_ambiguous_pool.csv', ['QAC_POS','lemma_Buckwalter','surface_Buckwalter','frequency'],
          [[tag,lem,form,n] for (tag,lem,form),n in q_ambig_counter.most_common()])
write_csv('22b_qac_interrogative_conditional_token_review.csv',
          ['location','QAC_POS','surface_Buckwalter','lemma_Buckwalter','features'],
          [[r['loc'],r['tag'],r['form'],next((t[4:] for t in r['features'] if t.startswith('LEM:')), ''),'|'.join(r['features'])]
           for r in q_ambiguous])
write_csv('22a_qac_interrogative_conditional_ambiguous_summary.csv', ['QAC_POS','frequency','note'], [
    ['COND', sum(r['tag']=='COND' for r in q_ambiguous), 'Mixed conditional tag: includes conditional particles and conditional nouns; context-sensitive review required'],
    ['INTG', sum(r['tag']=='INTG' for r in q_ambiguous), 'Mixed interrogative tag: includes interrogative particles and interrogative nouns; context-sensitive review required'],
    ['TOTAL', len(q_ambiguous), 'Excluded from strict Ism denominator until token-level word-class review']
])

# QAC POS subset summaries
q_pools = {
    'Core noun/proper noun/adjective (N, PN, ADJ)': {'N','PN','ADJ'},
    'Core + time/place adverbs (N, PN, ADJ, T, LOC)': {'N','PN','ADJ','T','LOC'},
    'Broad Ism pool incl. pronouns/relatives/demonstratives': QAC_ISM_POS,
}
q_pool_rows = []
for pool_name, tags in q_pools.items():
    xs = [r for r in q_ism if r['tag'] in tags]
    q_pool_rows.append([pool_name, len(xs), len({q_word_key(r) for r in xs})])

# ---------------- Supplied MASAQ source CSV ----------------
with MASAQ_CSV.open('r', encoding='utf-8-sig', newline='') as f:
    mrows = list(csv.DictReader(f))

m_stems = [r for r in mrows if r['Morph_Type']=='Stem']
def is_masaq_ism_tag(t):
    return (t.startswith('NOUN_') or t.startswith('GERUND') or t.startswith('ADJ_') or t in {
        'ADV','DEM_PRON','DEM_PRON_F','DEM_PRON_FS','DEM_PRON_MP','DEM_PRON_MS',
        'EXCEPT_NOUN','FOREIGN','CURRENCY','ABBREV','PRON','REL_PRON','INTERROG_PRON','REL_ADV'
    })
m_ism = [r for r in m_stems if is_masaq_ism_tag(r['Morph_Tag'] or '')]
M_FAMILIES = {
    'Lexical nouns (common/proper/derived noun tags)': lambda t: t.startswith('NOUN_') or t in {'FOREIGN','CURRENCY','ABBREV','EXCEPT_NOUN'},
    'Verbal nouns / gerunds': lambda t: t.startswith('GERUND'),
    'Adjectives': lambda t: t.startswith('ADJ_'),
    'Pronouns / demonstratives / relative / interrogative': lambda t: t in {'PRON','REL_PRON','DEM_PRON','DEM_PRON_F','DEM_PRON_FS','DEM_PRON_MP','DEM_PRON_MS','INTERROG_PRON'},
    'Adverbial nouns': lambda t: t in {'ADV','REL_ADV'},
}

def mword(r): return (r['Sura_No'], r['Verse_No'], r['Word_No'])
m_ism_word_keys = {mword(r) for r in m_ism}
m_ism_tag_counts = Counter(r['Morph_Tag'] for r in m_ism)
m_family_counts = Counter()
for r in m_ism:
    for fam, fn in M_FAMILIES.items():
        if fn(r['Morph_Tag']):
            m_family_counts[fam] += 1
            break

m_decl = Counter(r['Invariable_Declinable'] or 'UNMARKED' for r in m_ism)
m_case = Counter(r['Case_Mood'] or 'UNMARKED' for r in m_ism)
m_marker = Counter(r['Case_Mood_Marker'] or 'UNMARKED' for r in m_ism)
m_construct = Counter(r['Possessive_Construct'] or 'UNMARKED' for r in m_ism)

# MASAQ word-level definiteness cues linked to Ism stems.
m_prefix_article_rows = [r for r in mrows if r['Morph_Type']=='Prefix' and r['Morph_Tag']=='DET' and r['Segmented_Word']=='ال']
m_article_keys = {mword(r) for r in m_prefix_article_rows} & m_ism_word_keys
m_poss_rows = [r for r in mrows if r['Morph_Type']=='Suffix' and r['Morph_Tag']=='POSS_PRON']
m_poss_keys = {mword(r) for r in m_poss_rows} & m_ism_word_keys
m_def_suffix_tags = {'CASE_DEF_NOM','CASE_DEF_ACC','CASE_DEF_GEN'}
m_indef_suffix_tags = {'CASE_INDEF_NOM','CASE_INDEF_ACC','CASE_INDEF_GEN','CASE_INDEF_(ACC_GEN)'}
m_def_suff_rows = [r for r in mrows if r['Morph_Type']=='Suffix' and r['Morph_Tag'] in m_def_suffix_tags]
m_indef_suff_rows = [r for r in mrows if r['Morph_Type']=='Suffix' and r['Morph_Tag'] in m_indef_suffix_tags]
m_def_suff_keys = {mword(r) for r in m_def_suff_rows} & m_ism_word_keys
m_indef_suff_keys = {mword(r) for r in m_indef_suff_rows} & m_ism_word_keys
m_construct_keys = {mword(r) for r in m_ism if r['Possessive_Construct']=='CONSTRUCT'}

# ---------------- Write QAC outputs ----------------
write_csv('23_qac_ism_pos_distribution.csv', ['QAC_POS','frequency','pct_of_QAC_Ism_stem_rows','interpretation'], [
    [p, n, round(pct(n,len(q_ism)),4), {
        'N':'Common noun', 'PN':'Proper noun', 'ADJ':'Adjective', 'T':'Time adverb (nominal)',
        'LOC':'Locative adverb (nominal)', 'PRON':'Personal pronoun', 'REL':'Relative pronoun', 'DEM':'Demonstrative'
    }.get(p,'QAC tag')]
    for p,n in q_pos_counts.most_common()
])

for feature_name, c_all, by_pos, meaning in [
    ('gender', q_gender, q_gender_by_pos, {'M':'Masculine','F':'Feminine','UNMARKED':'No explicit gender feature','MIXED/CONFLICT':'Conflicting feature tokens'}),
    ('number', q_number, q_number_by_pos, {'S':'Singular','D':'Dual','P':'Plural','UNMARKED':'No explicit number feature','MIXED/CONFLICT':'Conflicting feature tokens'}),
    ('case', q_case, q_case_by_pos, {'NOM':'Nominative / Rafʿ','ACC':'Accusative / Naṣb','GEN':'Genitive / Jarr','UNMARKED':'No explicit case feature'}),
    ('definiteness_state', q_state, q_state_by_pos, {'DEF':'Explicit DEF tag','INDEF':'Explicit INDEF tag','UNMARKED':'No explicit state tag'}),
]:
    den = len(q_ism)
    rows = []
    for cat,n in c_all.most_common():
        rows.append(['ALL_ISM',cat,n,round(pct(n,den),4), meaning.get(cat,cat),den])
    for pos in sorted(by_pos):
        d = sum(by_pos[pos].values())
        for cat,n in by_pos[pos].most_common():
            rows.append([pos,cat,n,round(pct(n,d),4),meaning.get(cat,cat),d])
    write_csv(f'24_qac_ism_{feature_name}_distribution.csv', ['QAC_POS_or_ALL','feature_value','frequency','pct_within_denominator','label','denominator'], rows)

# Marked-only ratio views for gender and number
for feat,c in [('gender',q_gender),('number',q_number)]:
    marked = sum(n for k,n in c.items() if k not in {'UNMARKED','MIXED/CONFLICT'})
    rows=[]
    for k,n in c.most_common():
        if k not in {'UNMARKED','MIXED/CONFLICT'}:
            rows.append([k,n,round(pct(n,marked),4),marked,'Marked-feature subset only'])
        else:
            rows.append([k,n,round(pct(n,len(q_ism)),4),len(q_ism),'Coverage / missingness against all Ism rows'])
    write_csv(f'25_qac_ism_{feat}_marked_subset.csv',['feature_value','frequency','percentage','denominator','interpretation'],rows)

write_csv('26_qac_ism_pool_comparison.csv',['pool_definition','stem_annotation_rows','unique_word_positions'],q_pool_rows)

# Definite / indefinite cue classes at unique QAC word-position level
write_csv('27_qac_ism_definiteness_evidence_distribution.csv',
          ['evidence_class','unique_word_positions','pct_of_unique_Ism_word_positions','assignment_rule'],
          [[k,v,round(pct(v,len(q_ism_keys)),4),{
              'Explicit INDEF state':'QAC feature INDEF; takes priority over POS-based definite classification where labels conflict',
              'Al- article prefix':'Word has a DET/PREFIX segment with Al+; may overlap PN in source, assigned once here',
              'Pronoun / relative / demonstrative (inherently definite)':'STEM POS is PRON, REL, or DEM',
              'Proper noun (inherently definite)':'STEM POS is PN, excluding article-bearing and explicitly INDEF-marked cases',
              'Attached pronoun suffix (possessive/annexed)':'Word has PRON/SUFFIX and Ism STEM; only when no higher-priority marker exists',
              'Definiteness not determined by available marker':'No explicit state, article, pronoun/PN class, or attached-pronoun cue in these exports'
          }.get(k,'')]
           for k,v in q_def_class_counts.most_common()])
write_csv('28_qac_ism_definiteness_marker_overlap.csv',['overlap_pair','unique_word_positions'],q_overlaps)

# Case table with both all-Ism and case-marked denominators
case_marked = sum(q_case[k] for k in ('NOM','ACC','GEN'))
write_csv('29_qac_ism_case_distribution_summary.csv',
          ['case_state','frequency','pct_of_all_Ism_stem_rows','pct_of_case_marked_subset','all_Ism_denominator','case_marked_denominator'],
          [[k,q_case.get(k,0),round(pct(q_case.get(k,0),len(q_ism)),4),round(pct(q_case.get(k,0),case_marked),4),len(q_ism),case_marked]
           for k in ('NOM','ACC','GEN','UNMARKED')])

# ---------------- Write MASAQ outputs ----------------
write_csv('30_masaq_ism_pos_tag_distribution.csv',['Morph_Tag','frequency','pct_of_MASAQ_Ism_stem_rows'],
          [[k,v,round(pct(v,len(m_ism)),4)] for k,v in m_ism_tag_counts.most_common()])
write_csv('31_masaq_ism_family_distribution.csv',['Ism_family','frequency','pct_of_MASAQ_Ism_stem_rows'],
          [[k,v,round(pct(v,len(m_ism)),4)] for k,v in m_family_counts.most_common()])

for fname, title, c, denom in [
    ('32_masaq_ism_declineability_labels.csv','Invariable_Declinable',m_decl,len(m_ism)),
    ('33_masaq_ism_case_mood_labels.csv','Case_Mood',m_case,len(m_ism)),
    ('34_masaq_ism_case_marker_labels.csv','Case_Mood_Marker',m_marker,len(m_ism)),
    ('35_masaq_ism_possessive_construct.csv','Possessive_Construct',m_construct,len(m_ism)),
]:
    write_csv(fname,[title,'frequency','pct_of_MASAQ_Ism_stem_rows'],[[k,v,round(pct(v,denom),4)] for k,v in c.most_common()])

# Family x feature tables
for col, label in [('Invariable_Declinable','declinability'),('Case_Mood','case_mood'),('Possessive_Construct','possessive_construct')]:
    rows=[]
    for fam,fn in M_FAMILIES.items():
        xs=[r for r in m_ism if fn(r['Morph_Tag'])]
        c=Counter(r[col] or 'UNMARKED' for r in xs)
        den=len(xs)
        for k,v in c.most_common():
            rows.append([fam,k,v,round(pct(v,den),4),den])
    write_csv(f'36_masaq_ism_family_by_{label}.csv',['Ism_family',col,'frequency','pct_within_family','family_denominator'],rows)

# MASAQ word-level definiteness cue counts (unique word positions, with overlap kept separate)
write_csv('37_masaq_ism_definiteness_marker_coverage.csv',
          ['marker_or_feature','unique_Ism_word_positions','source_segment_or_field','interpretation'],[
              ['Al- article prefix',len(m_article_keys),'Prefix Morph_Tag=DET and Segmented_Word=ال','Explicit al- prefix; source CSV has additional DET rows not equal to the Arabic definite article'],
              ['Attached POSS_PRON suffix',len(m_poss_keys),'Suffix Morph_Tag=POSS_PRON','Attached pronoun suffix on a word with an Ism stem; indicates annexed/possessive relationship but host can be a prep or other type depending alignment'],
              ['CASE_DEF_* suffix',len(m_def_suff_keys),'Suffix Morph_Tag=CASE_DEF_NOM/ACC/GEN','Definite case-ending suffix labels; subset only, not full definiteness coverage'],
              ['CASE_INDEF_* suffix',len(m_indef_suff_keys),'Suffix Morph_Tag=CASE_INDEF_*','Indefinite case-ending suffix labels; subset only, not full definiteness coverage'],
              ['Construct / Mudaf head',len(m_construct_keys),'Stem Possessive_Construct=CONSTRUCT','Idafa-head marker; does not by itself tell whether the Mudaf is definite'],
          ])


# POS-level definiteness evidence coverage (unique word positions per POS).
q_def_pos_rows=[]
for pos in sorted(QAC_ISM_POS):
    pos_rows=[r for r in q_ism if r['tag']==pos]
    pos_keys={q_word_key(r) for r in pos_rows}
    q_def_pos_rows.append([pos,len(pos_rows),len(pos_keys),len(pos_keys & q_indef_keys),len(pos_keys & q_article_keys),len(pos_keys & q_pron_suffix_keys),len(pos_keys & q_intrinsic_pron_keys),len(pos_keys & q_pn_keys)])
write_csv('39_qac_ism_definiteness_evidence_by_pos.csv',
          ['QAC_POS','stem_rows','unique_word_positions','INDEF_state_word_positions','Al_article_word_positions','attached_PRON_suffix_word_positions','intrinsically_definite_pronoun_POS_word_positions','proper_noun_POS_word_positions'],q_def_pos_rows)

# MASAQ family by case-marker labels.
rows=[]
for fam,fn in M_FAMILIES.items():
    xs=[r for r in m_ism if fn(r['Morph_Tag'])]
    c=Counter(r['Case_Mood_Marker'] or 'UNMARKED' for r in xs)
    den=len(xs)
    for k,v in c.most_common():
        rows.append([fam,k,v,round(pct(v,den),4),den])
write_csv('40_masaq_ism_family_by_case_marker.csv',['Ism_family','Case_Mood_Marker','frequency','pct_within_family','family_denominator'],rows)

# MASAQ jussive records in an Ism-candidate stem group: editorial review queue.
review_rows=[]
for r in m_ism:
    if r['Case_Mood']=='JUSSIVE':
        review_rows.append([r['Sura_No'],r['Verse_No'],r['Word_No'],r['Word'],r['Segmented_Word'],r['Morph_Tag'],r['Invariable_Declinable'],r['Case_Mood_Marker'],r['Gloss']])
write_csv('41_masaq_ism_jussive_annotation_review.csv', ['Sura_No','Verse_No','Word_No','Word','Segmented_Word','Morph_Tag','Invariable_Declinable','Case_Mood_Marker','Gloss'],review_rows)

# QAC coverage summary for the four high-level properties.
q_feature_coverage_rows=[]
for prop, counts, known in [
    ('Gender',q_gender, sum(v for k,v in q_gender.items() if k not in {'UNMARKED','MIXED/CONFLICT'})),
    ('Number',q_number, sum(v for k,v in q_number.items() if k not in {'UNMARKED','MIXED/CONFLICT'})),
    ("I'rab case",q_case, sum(v for k,v in q_case.items() if k in {'NOM','ACC','GEN'})),
    ('Definiteness state',q_state, sum(v for k,v in q_state.items() if k in {'DEF','INDEF'})),
]:
    q_feature_coverage_rows.append([prop,known,len(q_ism)-known,round(pct(known,len(q_ism)),4),len(q_ism)])
write_csv('42_qac_ism_feature_annotation_coverage.csv',['property','rows_with_explicit_feature','rows_unmarked_or_unresolved','coverage_pct','denominator'],q_feature_coverage_rows)

# Full dataset profile / data quality checks
write_csv('38_ism_source_population_and_scope.csv',
          ['source','population','count','unit','scope_or_note'],[
              ['QAC morphology 0.4', 'All STEM rows',len(q_stems),'stem annotation rows','Official QAC download; coordinates preserved'],
              ['QAC morphology 0.4', 'Broad Ism POS set',len(q_ism),'stem annotation rows','N, PN, ADJ, T, LOC, PRON, REL, DEM'],
              ['QAC morphology 0.4', 'Broad Ism POS set',len(q_ism_keys),'unique word positions','5 word positions contain two Ism STEM analyses; feature-distribution denominators use STEM rows unless noted'],
              ['MASAQ CSV (supplied archive)', 'All annotation rows',len(mrows),'CSV data rows','Exact data-row count in the supplied MASAQ.csv file; not claimed to match the article profile'],
              ['MASAQ CSV (supplied archive)', 'All Stem rows',len(m_stems),'stem segment rows','Segment-level MASAQ CSV'],
              ['MASAQ CSV (supplied archive)', 'Broad Ism stem set',len(m_ism),'stem segment rows','Derived from Morph_Tag family taxonomy; 5 disjoint learner-facing families'],
              ['MASAQ CSV (supplied archive)', 'Broad Ism stem set',len(m_ism_word_keys),'unique word positions','A word can have more than one segment; rows are the morphology unit'],
              ['QAC vs MASAQ', 'Broad Ism count difference',len(q_ism)-len(m_ism),'stem rows','Different tagsets/definitions/version profiles; do not pool or sum across sources'],
          ])

# README with all caveats
readme = '''QUANTITATIVE ISM FEATURE DISTRIBUTIONS - METHODS AND LIMITATIONS

Scope
This addendum provides Quran-wide quantitative distributions for the four traditional learner-facing Ism properties:
(1) definiteness, (2) gender, (3) number, and (4) I'rab/case. It also reports declinability, case-marker labels, Ism subtype families, and Idafa/construct status.

Sources and populations
1) Quranic Arabic Corpus morphology v0.4 (QAC): 77,915 STEM annotations in the raw 0.4 morphology file. The operational broad Ism pool includes QAC POS N, PN, ADJ, T, LOC, PRON, REL and DEM: 40,778 STEM annotation rows across 40,773 unique word positions. In traditional grammar, personal/relative/demonstrative pronouns and temporal/locative adverbs are treated as Ism-like; the table therefore keeps both the core nominal and broad pool definitions visible.
2) Supplied MASAQ source CSV: 77,797 Stem segment rows; 39,237 rows are classified as Ism-like using its NOUN_*, GERUND*, ADJ_*, ADV, pronoun, demonstrative, relative, interrogative and related nominal tags. These are segment-level annotations. The MASAQ and QAC populations are NOT interchangeable and must not be added together.

Feature extraction and denominators
- QAC POS membership is anchored to the raw morphology v0.4 file; gender, number, case and nominal-state values are joined from the companion Quranic.csv by exact (sura:ayah:word:segment) location. The join covers all 40,778 QAC Ism STEM locations and preserves compound inflection values supplied in the structured columns.
- QAC gender and number tables display all Ism STEM rows, including UNMARKED, and then a marked-subset table. UNMARKED means no explicit feature in the source, not a grammatical value.
- QAC case distribution includes NOM, ACC, GEN; these are the three noun cases. Rows with no case feature are retained as UNMARKED. The QAC file has no explicit DEF tag in this version; INDEF is present for a subset.
- QAC definiteness is reported as marker/evidence classes over unique Ism word positions, not as a false binary total. Evidence: explicit INDEF feature; Al+ article prefix; inherent definite POS classes (PN, PRON, REL, DEM); attached PRON suffix on an Ism word. Precedence resolves overlaps once per word. Residual records are not automatically called Nakirah or Ma'rifah.
- MASAQ family counts and declinability/case features are based on Morph_Type='Stem' and the specified nominal Morph_Tag family rules. MASAQ Case_Mood values INVARIABLE and JUSSIVE are retained as raw annotations, not taught as noun case states. JUSSIVE on 6 Ism-candidate rows is flagged for review; it is not a fourth Ism case.
- MASAQ Case_Mood_Marker values are shown verbatim. Codes with IMP_ are not reinterpreted here because the available public field documentation does not provide a sufficiently authoritative value-by-value codebook. SUKUN is a source annotation, not an additional noun case.
- MASAQ Possessive_Construct=CONSTRUCT identifies a construct head and is not itself the same as definiteness. A Mudaf becomes definite only when the Mudaf ilayh is definite; this file does not fully determine that in every case.

Important reconciliation points
- Raw QAC v0.4 morphology text and the accompanying Quranic.csv export disagree on 132 segment POS assignments. This addendum uses raw v0.4 for Ism POS membership, then joins feature fields from Quranic.csv by exact location. All 40,778 Ism STEM locations join; the output therefore preserves the raw source POS population but uses structured companion fields for gender, number, case and nominal-state values.
- The previous addendum used a stale nominal case summary of 31,914. This raw-source calculation replaces it with current QAC values shown in the CSVs; do not reuse the stale summary.
- The QAC broad Ism pool contains 40,778 stem annotations but 40,773 unique word positions because five word positions have two Ism stem analyses. STEM-row feature tables use 40,778; definiteness cue classifications use 40,773 unique word positions.
- The MASAQ research article reports 8,365 definite-article tokens. The supplied archive CSV has 10,913 Prefix rows with Segmented_Word='ال'. The supplied archive CSV row count and header/profile do not fully reconcile with the article's published profile, so the exact dataset snapshot and counting unit are not independently confirmed. The 10,913 figure is therefore labelled as a direct count from the supplied CSV, not a verified V6 count.

Interpretation safeguards
- Do not treat UNMARKED as masculine, singular, definite, or indefinite.
- Do not teach Jussive as a noun case, and do not teach Sukoon as an additional noun case.
- Do not merge QAC and MASAQ counts. They use different tagsets, row units, coverage, and annotation rules.
- All categories should receive qualified Arabic grammar review before appearing as prescriptive lessons or answer keys.

Licensing / provenance
- QAC source: Quranic Arabic Corpus morphology v0.4; its source file states GNU GPL and asks that the corpus be credited with a link to corpus.quran.com when used in an application. Preserve its copyright notice and terms.
- A separate Mendeley Data V6 record (DOI 10.17632/9yvrzxktmr.6) states CC BY-NC 3.0. Because the supplied archive CSV is not fully reconciled to the publication profile, do not assume that it is the exact V6 snapshot or that the V6 license attribution alone clears the archive file for reuse. Verify source provenance and obtain rights advice before commercial use.
- This addendum contains calculated aggregate statistics and taxonomy mappings, not redistributed source records.
'''
(OUT/'README_Methodology_and_Limitations.txt').write_text(readme,encoding='utf-8')

# Small machine-readable overview JSON
summary = {
    'qac_v0_4': {
        'all_stem_rows': len(q_stems), 'broad_ism_stem_rows': len(q_ism), 'broad_ism_unique_words': len(q_ism_keys),
        'pos_counts': dict(q_pos_counts), 'gender': dict(q_gender), 'number': dict(q_number), 'case': dict(q_case),
        'state': dict(q_state), 'definiteness_evidence': dict(q_def_class_counts),
        'definiteness_overlaps': q_overlaps, 'case_marked_denominator': case_marked,
    },
    'masaq_archive_csv': {
        'all_stem_rows': len(m_stems), 'ism_stem_rows': len(m_ism), 'ism_unique_words': len(m_ism_word_keys),
        'family_counts': dict(m_family_counts), 'declinability': dict(m_decl), 'case_mood': dict(m_case),
        'case_markers': dict(m_marker), 'possessive_construct': dict(m_construct),
        'definiteness_marker_coverage': {
            'article_al_prefix_unique_words':len(m_article_keys), 'attached_poss_pron_unique_words':len(m_poss_keys),
            'case_def_suffix_unique_words':len(m_def_suff_keys), 'case_indef_suffix_unique_words':len(m_indef_suff_keys),
            'construct_head_unique_words':len(m_construct_keys)
        }
    }
}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
