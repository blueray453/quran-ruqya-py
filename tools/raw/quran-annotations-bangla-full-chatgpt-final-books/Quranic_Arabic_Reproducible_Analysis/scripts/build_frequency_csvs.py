#!/usr/bin/env python3
"""Create the core vocabulary, verb, and phrase/role CSVs from bundled source data.

All paths are supplied on the command line. Uses only Python's standard library.
"""
from __future__ import annotations
import argparse, csv, json, re, sqlite3, collections, math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def pct(n: int, d: int) -> float:
    return round(100.0*n/d, 6) if d else 0.0


def write_csv(path: Path, headers: List[str], rows: Iterable[Iterable[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def read_csv(path: Path, encoding='utf-8-sig', delimiter=',') -> List[dict]:
    with path.open('r', encoding=encoding, newline='') as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def loc_parts(loc: str):
    m = re.fullmatch(r'(\d+):(\d+):(\d+)', str(loc or ''))
    if not m: return None
    return tuple(map(int, m.groups()))


def full_loc_parts(loc: str):
    m = re.fullmatch(r'\((\d+):(\d+):(\d+):(\d+)\)', str(loc or ''))
    if not m: return None
    return tuple(map(int, m.groups()))


def ranked_count_rows(counter: collections.Counter, denominator: int, label_name: str,
                       source_rows: Dict[str, list] | None = None):
    rows=[]; cum=0
    for rank,(label,n) in enumerate(sorted(counter.items(), key=lambda kv:(-kv[1], str(kv[0]))),1):
        cum += n
        rows.append([rank,label,n,pct(n,denominator),cum,pct(cum,denominator)])
    return rows


def build_qul(data_dir: Path, out: Path) -> dict:
    wbw_path=data_dir/'quran-script'/'wbw'/'uthmani-wbw.json'
    wbw=json.loads(wbw_path.read_text(encoding='utf-8'))
    surface=collections.Counter(); locations=collections.defaultdict(list)
    ayahs=collections.defaultdict(set); surahs=collections.defaultdict(set)
    digit_re=re.compile(r'^[٠-٩]+$')
    total=0
    for key,obj in wbw.items():
        text=str(obj.get('text','')).strip()
        if not text or digit_re.fullmatch(text):
            continue  # verse-number marker, not a Quranic word token
        total += 1
        surface[text] += 1
        loc=str(obj.get('location') or key)
        locations[text].append(loc)
        parts=loc_parts(loc)
        if parts:
            s,a,_=parts; ayahs[text].add((s,a)); surahs[text].add(s)
    rows=[]; cum=0
    for rank,(term,n) in enumerate(sorted(surface.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n
        rows.append([rank,term,n,pct(n,total),cum,pct(cum,total),len(ayahs[term]),len(surahs[term]),';'.join(locations[term])])
    write_csv(out/'vocabulary_surface_frequency.csv',
              ['rank','surface_form_uthmani','frequency','pct_of_quranic_word_tokens','cumulative_frequency','cumulative_pct','unique_ayahs','unique_surahs','occurrence_locations'],rows)

    map_stats=[]
    for unit,db_name,main_table,word_table,text_col,clean_col,output_name,label_headers in [
        ('lemma','word-lemma.db','lemmas','lemma_words','text','text_clean','vocabulary_lemma_frequency.csv',
         ['rank','lemma_arabic','lookup_or_normalized','frequency','pct_of_mapped_occurrences','cumulative_frequency','cumulative_pct','unique_word_locations']),
        ('stem','word-stem.db','stems','stem_words','text','text_clean','vocabulary_stem_frequency.csv',
         ['rank','stem_form','lookup_or_normalized','frequency','pct_of_mapped_occurrences','cumulative_frequency','cumulative_pct','unique_word_locations']),
        ('root','word-root.db','roots','root_words','arabic_trilateral','english_trilateral','vocabulary_root_frequency.csv',
         ['rank','root_arabic','root_transliteration','frequency','pct_of_mapped_occurrences','cumulative_frequency','cumulative_pct','unique_word_locations'])
    ]:
        con=sqlite3.connect(data_dir/'grammar'/db_name)
        try:
            cur=con.cursor()
            terms=cur.execute(f'SELECT id,{text_col},{clean_col} FROM {main_table}').fetchall()
            mapping=collections.defaultdict(list)
            for ident,loc in cur.execute(f'SELECT {unit}_id,word_location FROM {word_table}'):
                mapping[ident].append(loc)
            records=[]
            for ident,term,clean in terms:
                locs=mapping.get(ident,[])
                if not locs: continue
                records.append((str(term or ''),str(clean or ''),locs))
            records.sort(key=lambda x:(-len(x[2]),x[0],x[1]))
            denom=sum(len(r[2]) for r in records); cum=0; table=[]
            for rank,(term,clean,locs) in enumerate(records,1):
                n=len(locs); cum+=n
                if unit=='root': table.append([rank,term,clean,n,pct(n,denom),cum,pct(cum,denom),len(set(locs))])
                else: table.append([rank,term,clean,n,pct(n,denom),cum,pct(cum,denom),len(set(locs))])
            write_csv(out/output_name,label_headers,table)
            counts=collections.Counter()
            for term,clean,locs in records: counts[term]=len(locs)
            top='; '.join(f'{term}:{n}' for term,n in counts.most_common(10))
            map_stats.append([unit,denom,len({loc for _,_,ls in records for loc in ls}),len(records),len(terms),len(terms)-len(records),pct(denom,total),top])
        finally: con.close()
    write_csv(out/'dataset_mapping_coverage.csv',
              ['resource','mapped_occurrences','unique_word_locations','terms_with_occurrences','total_lexicon_terms','terms_without_occurrences','pct_of_quran_tokens_mapped','top_10_examples'],map_stats)

    # Coverage thresholds are based on ranked Uthmani surface types.
    threshold_rows=[]
    ordered=sorted(surface.items(),key=lambda kv:(-kv[1],kv[0]))
    for target in [50,60,70,80,85,90,95]:
        cum=0; forms=0
        for _,n in ordered:
            cum+=n; forms+=1
            if cum/total*100 >= target: break
        threshold_rows.append([target,forms,cum,pct(cum,total)])
    write_csv(out/'18_vocabulary_surface_coverage_thresholds.csv',
              ['target_coverage_pct','distinct_surface_forms_required','tokens_covered_at_threshold','actual_coverage_pct'],threshold_rows)
    summary=[]
    for unit,records,denom in [('surface',surface,total),
                               ('lemma',None,dict(map_stats).get('lemma',0) if False else 0)]:
        if unit=='surface': summary.append([unit,total,len(surface),total,pct(total,total),'77,432 target comparison'])
    for row in map_stats:
        unit,records,unique,terms,total_terms,unmapped_terms,coverage,top=row
        summary.append([unit,records,terms,unique,coverage,top])
    write_csv(out/'17_vocabulary_coverage_summary.csv',
              ['mapping_unit','mapped_occurrences','distinct_terms','unique_word_locations','pct_of_surface_tokens_mapped','top_examples'],summary)
    return {'surface_tokens':total,'surface_types':len(surface),'mapping':map_stats}


def read_qac_morphology(path: Path) -> list:
    records=[]
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            line=line.rstrip('\n\r')
            if not line or line.startswith('#') or line.startswith('LOCATION'):
                continue
            parts=line.split('\t')
            if len(parts)<4: continue
            loc,form,tag,feat=parts[:4]
            m=full_loc_parts(loc)
            if not m: continue
            features=feat.split('|')
            if 'STEM' not in features: continue
            s,a,w,seg=m
            records.append({'loc':loc,'sura':s,'ayah':a,'word':w,'segment':seg,'form':form,'tag':tag,'features':features})
    return records


def extract_person(features):
    vals=set()
    for f in features:
        m=re.match(r'^([123])',f)
        if m and f not in {'3','2','1'} or f in {'1','2','3'}:
            if m: vals.add(m.group(1))
            elif f in {'1','2','3'}: vals.add(f)
    if len(vals)==1: return next(iter(vals))
    if len(vals)>1: return 'MIXED/CONFLICT'
    return 'UNMARKED_OR_DEFAULT'


def extract_gender(features):
    vals=set()
    for f in features:
        if f in {'M','F'}: vals.add(f)
        m=re.fullmatch(r'(?:[123])?([MF])(?:[SDP])?',f)
        if m: vals.add(m.group(1))
    if len(vals)==1: return next(iter(vals))
    if len(vals)>1: return 'MIXED/CONFLICT'
    return 'UNMARKED_OR_DEFAULT'


def extract_number(features):
    vals=set()
    for f in features:
        if f in {'S','D','P'}: vals.add(f)
        m=re.fullmatch(r'(?:[123])?(?:[MF])?([SDP])',f)
        if m: vals.add(m.group(1))
    if len(vals)==1: return next(iter(vals))
    if len(vals)>1: return 'MIXED/CONFLICT'
    return 'UNMARKED_OR_DEFAULT'


def feature_table(records, feature_fn, field, labels=None, default_label='UNMARKED_OR_DEFAULT'):
    vals=collections.Counter(feature_fn(r['features']) for r in records)
    total=len(records); cum=0; rows=[]
    for rank,(val,n) in enumerate(sorted(vals.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n
        rows.append([rank,val,n,pct(n,total),cum,pct(cum,total),sum(1 for r in records if feature_fn(r['features'])==val)])
    return rows,vals


def build_qac_verb_and_pos(data_dir: Path, out: Path) -> dict:
    qac=read_qac_morphology(data_dir/'grammar'/'quranic-corpus-morphology-0.4.txt')
    pos=collections.Counter(r['tag'] for r in qac)
    pos_rows=[]; cum=0; den=len(qac)
    # QAC POS dictionary, when provided.
    pos_defs={}
    ppos=data_dir/'grammar'/'CAPoS.csv'
    if ppos.exists():
        for r in read_csv(ppos,encoding='utf-16',delimiter='\t'):
            pos_defs[r.get('pos','')]=(r.get('pos_en',''),r.get('pos_ar',''))
    for rank,(tag,n) in enumerate(sorted(pos.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n; en,ar=pos_defs.get(tag,('',''))
        pos_rows.append([rank,tag,ar,en,n,pct(n,den),cum,pct(cum,den)])
    write_csv(out/'qac_pos_frequency.csv',['rank','pos','pos_arabic','pos_english','frequency','percentage','cumulative_frequency','cumulative_percentage'],pos_rows)

    verbs=[r for r in qac if r['tag']=='V']
    if len(verbs)!=19356:
        # A hard-coded assertion guards accidental parser changes against the current source file profile.
        raise ValueError(f'QAC verb stem count changed: expected 19,356, found {len(verbs)}')
    dimensions={
      'sarf_verb_form_frequency.csv':('verb_form',lambda r: next((f[1:-1] for f in r['features'] if re.fullmatch(r'\([IVX]+\)',f)),'I (default)')),
      'sarf_verb_aspect_frequency.csv':('verb_aspect',lambda r: next((f for f in r['features'] if f in {'PERF','IMPF','IMPV'}),'UNMARKED')),
      'sarf_verb_voice_frequency.csv':('verb_voice',lambda r: 'PASS' if 'PASS' in r['features'] else 'ACTIVE (default)'),
      'sarf_verb_person_frequency.csv':('person',extract_person),
      'sarf_verb_gender_frequency.csv':('gender',extract_gender),
      'sarf_verb_number_frequency.csv':('number',extract_number),
    }
    summaries={}
    for filename,(label,fn) in dimensions.items():
        counter=collections.Counter(fn(r) for r in verbs); total=len(verbs); cum=0; rows=[]
        for rank,(val,n) in enumerate(sorted(counter.items(),key=lambda kv:(-kv[1],kv[0])),1):
            cum+=n
            matching=[r for r in verbs if fn(r)==val]
            ayahs={(r['sura'],r['ayah']) for r in matching}; surahs={r['sura'] for r in matching}
            rows.append([rank,val,n,pct(n,total),cum,pct(cum,total),len(matching),len(ayahs),len(surahs)])
        write_csv(out/filename,['rank',label,'frequency','percentage_of_verb_occurrences','cumulative_frequency','cumulative_percentage','unique_word_positions','unique_ayahs','unique_surahs'],rows)
        summaries[label]=counter

    # Mood is defined only for imperfect verbs. Past and imperative verbs are not assigned indicative mood.
    imperfect=[r for r in verbs if 'IMPF' in r['features']]
    moods=collections.Counter('JUS' if 'MOOD:JUS' in r['features'] else 'SUBJ' if 'MOOD:SUBJ' in r['features'] else 'INDICATIVE (default)' for r in imperfect)
    rows=[]; cum=0; total=len(imperfect)
    for rank,(val,n) in enumerate(sorted(moods.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n; matching=[r for r in imperfect if ('JUS' if 'MOOD:JUS' in r['features'] else 'SUBJ' if 'MOOD:SUBJ' in r['features'] else 'INDICATIVE (default)')==val]
        rows.append([rank,val,n,pct(n,total),cum,pct(cum,total),len(matching),len({(r['sura'],r['ayah']) for r in matching}),len({r['sura'] for r in matching})])
    write_csv(out/'04d_fiil_mood_frequency_imperfect_only.csv',['rank','verb_mood','frequency','percentage_of_imperfect_verb_occurrences','cumulative_frequency','cumulative_percentage','unique_word_positions','unique_ayahs','unique_surahs'],rows)

    # A combined long-form table avoids treating dimensions as mutually exclusive.
    combo=[]
    for dim,counter in [('Form',summaries['verb_form']),('Aspect',summaries['verb_aspect']),('Voice',summaries['verb_voice']),('Person',summaries['person']),('Gender',summaries['gender']),('Number',summaries['number'])]:
        denom=len(verbs)
        for val,n in counter.most_common(): combo.append([dim,val,n,denom,pct(n,denom),'Dimensions overlap; do not sum across dimensions'])
    for val,n in moods.most_common(): combo.append(['Imperfect mood',val,n,len(imperfect),pct(n,len(imperfect)),'Mood denominator is imperfect verbs only'])
    write_csv(out/'16_verb_feature_frequency_combined.csv',['dimension','feature_value','frequency','denominator','percentage','interpretation_note'],combo)

    # Joint feature bundle frequency; useful for compound drill design.
    bundles=collections.Counter()
    for r in verbs:
        aspect=next((f for f in r['features'] if f in {'PERF','IMPF','IMPV'}),'UNMARKED')
        form=next((f[1:-1] for f in r['features'] if re.fullmatch(r'\([IVX]+\)',f)),'I')
        voice='PASS' if 'PASS' in r['features'] else 'ACTIVE'
        person=extract_person(r['features']); gender=extract_gender(r['features']); number=extract_number(r['features'])
        mood='-' if aspect!='IMPF' else ('JUS' if 'MOOD:JUS' in r['features'] else 'SUBJ' if 'MOOD:SUBJ' in r['features'] else 'IND')
        bundles[(form,aspect,voice,person,gender,number,mood)] += 1
    rows=[]; cum=0
    for rank,(bundle,n) in enumerate(sorted(bundles.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n; rows.append([rank,*bundle,n,pct(n,len(verbs)),cum,pct(cum,len(verbs))])
    write_csv(out/'sarf_verb_feature_bundle_frequency.csv',['rank','form','aspect','voice','person','gender','number','imperfect_mood','frequency','percentage','cumulative_frequency','cumulative_percentage'],rows)
    write_csv(out/'04b_fiil_feature_bundle_frequency.csv',['rank','form','aspect','voice','person','gender','number','imperfect_mood','frequency','percentage','cumulative_frequency','cumulative_percentage'],rows)

    # Explicit derivational noun tags: active participle, passive participle, verbal noun.
    derived=collections.Counter()
    d_records=collections.defaultdict(list)
    for r in qac:
        fs=set(r['features'])
        if 'PCPL' in fs and 'ACT' in fs: key='ACT_PCPL'
        elif 'PCPL' in fs and 'PASS' in fs: key='PASS_PCPL'
        elif 'VN' in fs: key='VN'
        else: continue
        derived[key]+=1; d_records[key].append(r)
    total=sum(derived.values()); rows=[]; cum=0
    for rank,(k,n) in enumerate(sorted(derived.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n; rs=d_records[k]
        rows.append([rank,k,n,pct(n,total),cum,pct(cum,total),len(rs),len({(r['sura'],r['ayah']) for r in rs}),len({r['sura'] for r in rs})])
    write_csv(out/'sarf_derived_noun_frequency.csv',['rank','derived_noun_category','frequency','percentage','cumulative_frequency','cumulative_percentage','unique_word_positions','unique_ayahs','unique_surahs'],rows)

    # Explicit pattern only; Form I is the QAC default and excluded here.
    pattern_counter=collections.Counter(); pattern_records=collections.defaultdict(list)
    for r in verbs:
        for f in r['features']:
            if re.fullmatch(r'\([IVX]+\)',f):
                pattern=f[1:-1]; pattern_counter[pattern]+=1; pattern_records[pattern].append(r); break
    rows=[]; cum=0; den=sum(pattern_counter.values())
    for rank,(k,n) in enumerate(sorted(pattern_counter.items(),key=lambda kv:(-kv[1],kv[0])),1):
        cum+=n; rs=pattern_records[k]
        rows.append([rank,f'({k})',n,pct(n,den),cum,pct(cum,den),len(rs),len({(r['sura'],r['ayah']) for r in rs}),len({r['sura'] for r in rs})])
    write_csv(out/'sarf_explicit_pattern_annotations.csv',['rank','source_form_tag','frequency','percentage_of_explicit_pattern_annotations','cumulative_frequency','cumulative_percentage','unique_word_positions','unique_ayahs','unique_surahs'],rows)
    return {'qac_stem_rows':len(qac),'qac_verb_stems':len(verbs),'imperfect_verb_stems':len(imperfect),'pos_types':len(pos)}


def build_qac_syntax(data_dir: Path, out: Path, ref_dir: Path) -> dict:
    qpath=data_dir/'grammar'/'Quranic.csv'
    qrows=read_csv(qpath,encoding='utf-16',delimiter='\t')
    # Relation codebook.
    rel_defs={}
    p=data_dir/'grammar'/'RelLabels.csv'
    if p.exists():
        for r in read_csv(p,encoding='utf-16',delimiter='\t'):
            rel_defs[r.get('rel_en','')]=(r.get('rel_id',''),r.get('rel_ar',''))
    rels=collections.defaultdict(list)
    for r in qrows:
        lab=(r.get('rel_label') or '').strip()
        if lab and lab not in {'root','NonRel','_','-'}:
            rels[lab].append(r)
    rel_total=sum(map(len,rels.values())); rows=[]; cum=0
    for rank,(lab,rs) in enumerate(sorted(rels.items(),key=lambda kv:(-len(kv[1]),kv[0])),1):
        n=len(rs); cum+=n; ids=set(); ay=set(); su=set(); unlocated=0
        for x in rs:
            loc=full_loc_parts(x.get('location',''))
            if loc: ids.add((loc[0],loc[1],loc[2]))
            else: unlocated+=1
            ch=(x.get('chapter_id') or '').strip(); ve=(x.get('verse_id') or '').strip()
            if ch and ve and ch!='_' and ve!='_': ay.add((ch,ve)); su.add(ch)
        rel_id,ar=rel_defs.get(lab,('',''))
        rows.append([rank,lab,ar,rel_id,n,pct(n,rel_total),cum,pct(cum,rel_total),len(ids),len(ay),pct(len(ay),6236),len(su),unlocated,'OBSERVED'])
    write_csv(out/'nahw_relationship_complete_qac.csv',['rank','original_relationship_label','arabic_label','source_relation_id','frequency','percentage_of_observed_relation_instances','cumulative_frequency','cumulative_percentage','unique_word_positions','unique_ayahs','ayah_incidence_pct','unique_surahs','virtual_or_unlocated_nodes','status'],rows)

    # Constituents/spans. Counts are annotation rows in the supplied QAC.csv export; not MASAQ phrase functions.
    const_defs={}
    p=data_dir/'grammar'/'ConstituentsTags.csv'
    if p.exists():
        for r in read_csv(p,encoding='utf-16',delimiter='\t'):
            const_defs[r.get('tag','')]=(r.get('tag_ar',''),r.get('tag_en',''))
    con_rows=[r for r in qrows if (r.get('constituent_label') or '').strip() not in {'','_','-'}]
    counts=collections.defaultdict(list)
    for r in con_rows: counts[r['constituent_label'].strip()].append(r)
    total=len(con_rows); rows=[]; cum=0
    for rank,(lab,rs) in enumerate(sorted(counts.items(),key=lambda kv:(-len(kv[1]),kv[0])),1):
        n=len(rs); cum+=n; ay=set(); su=set()
        for x in rs:
            ch=(x.get('chapter_id') or '').strip(); ve=(x.get('verse_id') or '').strip()
            if ch and ve and ch!='_' and ve!='_': ay.add((ch,ve)); su.add(ch)
        ar,en=const_defs.get(lab,('',''))
        rows.append([rank,lab,ar,en,n,pct(n,total),cum,pct(cum,total),len(ay),pct(len(ay),6236),len(su)])
    write_csv(out/'nahw_constituents_complete_qac.csv',['rank','constituent_tag','arabic_label','english_definition','frequency','percentage','cumulative_frequency','cumulative_percentage','unique_ayahs','ayah_incidence_pct','unique_surahs'],rows)
    # Compatibility view used by the analysis report.
    write_csv(out/'nahw_constituent_frequency_qac.csv',['rank','constituent_label','frequency','percentage_of_constituent_annotations','cumulative_frequency','cumulative_percentage','unique_ayahs','ayah_incidence_percentage','unique_surahs'],
              [[r[0],r[1],r[4],r[5],r[6],r[7],r[8],r[9],r[10]] for r in rows])
    # Report-ready translation and label fields.
    write_csv(out/'15_available_source_phrase_span_frequency.csv',['rank','source_label_code','source_label_arabic','source_label_english','source_span_count','pct_of_annotated_constituent_spans','cumulative_frequency','cumulative_percentage','unique_ayahs','ayah_incidence_pct','unique_surahs','unit_warning'],
              [[r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],'QAC.csv constituent annotation rows; not MASAQ phrase-instance counts'] for r in rows])
    write_csv(out/'01a_phrase_span_type_frequency_available.csv',['rank','source_label_code','source_label_english','frequency','percentage','unique_ayahs','unique_surahs','interpretation_note'],
              [[r[0],r[1],r[3],r[4],r[5],r[8],r[10],'QAC constituent annotation count; not the six teaching-pattern or MASAQ Phrasal_Function taxonomy'] for r in rows])
    return {'qac_csv_rows':len(qrows),'qac_relation_instances':rel_total,'qac_constituent_annotation_rows':total}


def build_masaq_roles(data_dir: Path, out: Path, ref_dir: Path) -> dict:
    mrows=read_csv(data_dir/'grammar'/'MASAQ.csv')
    role_counts=collections.defaultdict(list)
    for r in mrows:
        role=(r.get('Syntactic_Role') or '').strip()
        if role and role not in {'_','-','NA','N/A'}:
            role_counts[role].append(r)
    total=sum(map(len,role_counts.values()))
    defs={}
    p=ref_dir/'nahw_all_masaq_roles.csv'
    if p.exists():
        for r in read_csv(p): defs[r.get('masaq_role_code','')]=(r.get('english_definition',''),r.get('arabic_definition',''))
    rows=[]; cum=0
    for rank,(role,rs) in enumerate(sorted(role_counts.items(),key=lambda kv:(-len(kv[1]),kv[0])),1):
        n=len(rs); cum+=n; wordpos=set(); ay=set(); su=set()
        for x in rs:
            key=(x.get('Sura_No'),x.get('Verse_No'),x.get('Word_No'),x.get('Segment_No'))
            wordpos.add(key)
            if x.get('Sura_No') and x.get('Verse_No'): ay.add((x.get('Sura_No'),x.get('Verse_No'))); su.add(x.get('Sura_No'))
        en,ar=defs.get(role,('Definition not supplied in reference table',''))
        rows.append([rank,role,en,ar,n,pct(n,total),cum,pct(cum,total),len(ay),pct(len(ay),6236),len(su),'OBSERVED'])
    # Include reference roles with zero counts so the codebook remains complete.
    for role,(en,ar) in defs.items():
        if role not in role_counts: rows.append([0,role,en,ar,0,0,0,0,0,0,0,'ZERO_FREQUENCY'])
    rows.sort(key=lambda r:(r[0]==0,r[0],r[1]))
    write_csv(out/'nahw_all_masaq_roles.csv',['rank','masaq_role_code','english_definition','arabic_definition','frequency','percentage_of_observed_role_instances','cumulative_frequency','cumulative_percentage','unique_ayahs','ayah_incidence_pct','unique_surahs','status'],rows)
    rows2=[]
    for r in rows:
        rows2.append([r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],
                      'Word/segment-level annotation; do not interpret as phrase-span function frequency'])
    write_csv(out/'01d_masaq_word_role_frequency_not_phrase_function.csv',
              ['rank','masaq_role_code','english_definition','arabic_definition','frequency','percentage_of_observed_role_instances','cumulative_frequency','cumulative_percentage','unique_ayahs','ayah_incidence_pct','unique_surahs','interpretation_note'],rows2)
    return {'masaq_rows':len(mrows),'masaq_roles_observed':total,'masaq_unique_word_positions':len({(r.get('Sura_No'),r.get('Verse_No'),r.get('Word_No')) for r in mrows if r.get('Word_No')})}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data-dir',required=True,help='Root of extracted source_data directory')
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--reference-dir',required=True)
    args=ap.parse_args()
    data=Path(args.data_dir); out=Path(args.output_dir); ref=Path(args.reference_dir); out.mkdir(parents=True,exist_ok=True)
    summary={}
    summary['qul']=build_qul(data,out)
    summary['qac_morphology']=build_qac_verb_and_pos(data,out)
    summary['qac_syntax']=build_qac_syntax(data,out,ref)
    summary['masaq']=build_masaq_roles(data,out,ref)
    # Copy the static curated architecture/reference matrices. Quantitative tables are overwritten above or by Ism builder.
    static_files=['01b_teaching_phrase_pattern_frequency_template.csv','01c_phrase_function_frequency_template.csv',
      '02a_ism_four_properties_reference_and_status.csv','02b_ism_occurrence_features_output_schema.csv',
      '02e_ism_property_value_frequency_template.csv','03a_sample_ayah_phrase_chunks_al_fatiha.csv',
      '03b_ayah_phrase_chunking_rules.csv','03c_full_quran_ayah_phrase_chunk_output_schema.csv',
      '04a_fiil_properties_frequency.csv','04c_fiil_property_reference.csv',
      '10_traditional_grammar_architecture.csv','11_ism_four_properties_complete_taxonomy.csv',
      '13_phrase_construction_taxonomy.csv','14_phrase_function_taxonomy_masaq.csv']
    for name in static_files:
        src=ref/name
        if src.exists():
            (out/name).write_bytes(src.read_bytes())
        else:
            raise FileNotFoundError(f'Required reference table missing: {src}')
    # Machine-readable run profile.
    (out/'frequency_build_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
