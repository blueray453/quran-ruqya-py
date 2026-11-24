#!/usr/bin/env python3
"""Build a Quran-wide pedagogical phrase/chunk dataset from the bundled JSON sources.

The script preserves source annotations and keeps ILMHUB phrase constructions separate
from source-defined QAC constituents, dependency relations, and repeated lexical n-grams.
Only Python's standard library is required.
"""
from __future__ import annotations
import argparse, csv, json, hashlib, re
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data_sources"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "output" / "csv"

WORD_FILE = "indopak-nastaleeq-wbw-grammar-normalized.json"
SENT_FILE = "indopak-nastaleeq-sentence-grammar-normalized.json"
LEX_FILE = "quran-phrases-annotation.json"
LEX_EXACT_FILE = "quran-phrases-exact-diacritics-annotation.json"

# ILMHUB's core six are preserved as the core construction taxonomy.
NOMINAL_POS = {"N", "PN", "PRON", "DEM", "REM", "REL", "LOC", "T"}
ADJECTIVAL_POS = {"ADJ"}
COORD_NOMINAL_POS = NOMINAL_POS | ADJECTIVAL_POS
RELEVANT_RELATIONS = {
    "Poss", "Adj", "gen", "conj", "App", "Spec",
    "Subj", "Obj", "Pass", "Pred", "subj<<in>>", "pred<<in>>",
    "subj <<kan>>", "pred <<kan>>", "pred<<kan>>", "neg", "cond", "rslt", "sub",
}

CURRICULUM = [
    # Foundations - ILMHUB 3-2-6
    ("F01", "Foundations", "Kalimah / meaningful word", "Recognise Ism, Fi'l, Harf", "ILMHUB Foundations; Bayyinah Nahw Ch.1"),
    ("F02", "Foundations", "Murakkab", "Distinguish Murakkab Tamm (sentence) and Murakkab Naqis (phrase)", "ILMHUB Foundations"),
    ("F03", "Foundations", "Three word classes", "Ism, Fi'l, Harf", "ILMHUB Sections B; Bayyinah Nahw Ch.1"),
    ("F04", "Foundations", "Two sentence types", "Jumlah Ismiyyah and Jumlah Fi'liyyah", "ILMHUB Section C; Bayyinah Nahw Ch.5-6"),
    ("F05", "Foundations", "Six core phrase constructions", "Tawsifi, Idafi, Jarri, Ishari, Atfi, Badali", "ILMHUB Section D; Bayyinah Nahw Ch.2 and Ch.4"),
    # Ism four properties (DiGNI)
    ("I01", "Ism", "Definiteness", "Ma'rifah and Nakirah; definite categories; definiteness inheritance in Idafah", "ILMHUB Four Properties / The Ism; Bayyinah Nahw Ch.3 Type section (terminology to reconcile)"),
    ("I02", "Ism", "Gender", "Mudhakkar and Mu'annath; agreement", "ILMHUB Four Properties; Bayyinah Nahw Ch.3"),
    ("I03", "Ism", "Number", "Mufrad, Muthanna, Jam' (sound and broken plurals)", "ILMHUB Four Properties; Bayyinah Nahw Ch.3; Bayyinah Sarf Ch.13"),
    ("I04", "Ism", "I'rab", "Raf', Nasb, Jarr; primary and secondary signs; Mabni vs Mu'rab", "ILMHUB Four Properties / I'raab; Bayyinah Nahw Ch.2"),
    ("I05", "Ism", "Pronouns", "Independent and attached pronouns; pronoun as Mudaf Ilayhi / object", "Bayyinah Nahw Ch.2.5; Ch.6; ILMHUB Ism and Book 2"),
    # Six phrases
    ("P01", "Phrase", "Murakkab Tawsifi", "Described noun + adjective; four-property agreement", "ILMHUB Phrases; Bayyinah Nahw Ch.4.1"),
    ("P02", "Phrase", "Murakkab Idafi", "Mudaf + Mudaf Ilayhi; chains; pronoun/adverb as second member", "ILMHUB Phrases / Idafah; Bayyinah Nahw Ch.2.9"),
    ("P03", "Phrase", "Murakkab Jarri", "Harf Jarr + Majrur; Shibh al-Jumlah; attached prepositions", "ILMHUB Phrases / Harf Jarr; Bayyinah Nahw Ch.2.7"),
    ("P04", "Phrase", "Murakkab Ishari", "Demonstrative + definite noun; contrast phrase vs complete sentence", "ILMHUB Phrases; Bayyinah Nahw Ch.4.2"),
    ("P05", "Phrase", "Murakkab Atfi", "Conjunctive coordination and case inheritance", "ILMHUB Phrases; Bayyinah Nahw Ch.4.3"),
    ("P06", "Phrase", "Murakkab Badali", "Substitution/apposition candidate; second naming follows first in I'rab", "ILMHUB Phrases; Bayyinah source map (apposition to teacher review)"),
    # Sentence roles / clauses
    ("S01", "Sentence", "Nominal sentence", "Mubtada and Khabar; predicate order; Shibh al-Jumlah as Khabar", "ILMHUB Sentence section; Bayyinah Nahw Ch.5"),
    ("S02", "Sentence", "Verbal sentence", "Fi'l, Fa'il, Maf'ul Bih; embedded doer pronoun", "ILMHUB Book 2 Essential Parts; Bayyinah Nahw Ch.6-7"),
    ("S03", "Sentence", "Subject / Fa'il", "Explicit noun or embedded pronoun; phrase as sentence slot", "ILMHUB Book 2 Fa'il; Bayyinah Nahw Ch.6"),
    ("S04", "Sentence", "Object / Maf'ul Bih", "Noun or attached pronoun in Nasb; word-order variation", "ILMHUB Book 2; Bayyinah Nahw Ch.6"),
    ("S05", "Sentence", "Passive voice", "Na'ib al-Fa'il and passive sentence structure", "Bayyinah Nahw Ch.8"),
    ("S06", "Sentence", "Inna and sisters", "Ism Inna and Khabar Inna", "Bayyinah Nahw Ch.2.8; Ch.11"),
    ("S07", "Sentence", "Kana and sisters", "Ism Kana and Khabar Kana; change in case", "Bayyinah Nahw Ch.10"),
    ("S08", "Sentence", "Negation", "Negation of verbal and nominal sentences", "Bayyinah Nahw Ch.9"),
    ("S09", "Sentence", "Relative clauses", "Ism Mawصول, connector and subordinate clause", "Bayyinah Nahw Ch.5-7; source SC/REL relations"),
    ("S10", "Sentence", "Conditional clauses", "Shart and Jawab al-Shart", "Bayyinah Nahw complex sentence sections; source CS/cond/rslt"),
    ("V01", "Verb", "Madi / Mudari' / Amr", "Three main verbal forms and recognition", "ILMHUB Book 2 Essential Parts; Bayyinah Nahw Ch.6-7"),
    ("V02", "Verb", "Mudari' mood", "Raf', Nasb, Jazm applies to Mudari'; particles governing it", "Bayyinah Nahw Ch.7; QAC morphology"),
    ("V03", "Verb", "Verb forms and derived nouns", "Common forms, participles and verbal nouns", "ILMHUB Book 2 Morphology; Bayyinah Sarf Ch.1-3, 12"),
    ("H01", "Harf", "Prepositions", "Harf Jarr, governed Ism and attached pronouns", "85% guide Part I (reference method only); ILMHUB; Bayyinah Nahw Ch.2.7"),
    ("H02", "Harf", "Connectors", "Conjunctions and clause links", "85% guide Part I (reference method only); ILMHUB Atfi; Bayyinah Nahw Ch.4.3"),
    ("H03", "Harf", "Nasb/Jazm particles", "Particles with Mudari'; not to be confused with Ism case", "Bayyinah Nahw Ch.7"),
    ("H04", "Harf", "Negation / exception / question particles", "High-frequency function words in context", "85% guide Part I (reference method only); Bayyinah Nahw Ch.6, 9"),
    ("X01", "Comprehension", "Repeated lexical chunks", "Memorisable contiguous Quranic strings; no grammatical label implied", "85% guide frequency strategy (do not copy its protected lists); lexical n-gram corpus"),
]

SOURCE_ALIGNMENT = [
    ("Three word classes", "ILMHUB 3-2-6 foundations; Bayyinah Nahw Ch.1", "Retain as first formal classification", "Direct"),
    ("Two sentence types", "ILMHUB 3-2-6; Bayyinah Nahw Ch.5-6", "Retain nominal and verbal; do not infer sentence type solely from outermost Treebank tag", "Direct; corpus labels are constituent spans"),
    ("Six phrase constructions", "ILMHUB Section D; Bayyinah Ch.2 and Ch.4", "Retain exactly as core phrase taxonomy", "Direct"),
    ("Tawsifi", "ILMHUB Phrases; Bayyinah Ch.4.1", "Require noun/adjective dependency evidence; agreement is teachable feature layer", "Relation-derived; review edge cases"),
    ("Idafi", "ILMHUB Phrases/Idafah; Bayyinah Ch.2.9", "Use Poss dependency; expose chains and attached-pronoun Idafah", "Relation-derived; segment-aware"),
    ("Jarri", "ILMHUB Phrases/Harf Jarr; Bayyinah Ch.2.7", "Use preposition-to-genitive dependency and explicit PP spans", "Relation-derived; may be one written word when prefix attached"),
    ("Ishari", "ILMHUB Phrases; Bayyinah Ch.4.2", "Require demonstrative and a definite target; an indefinite target may form a complete sentence instead", "Conservative filter; candidates flagged"),
    ("Atfi", "ILMHUB Phrases; Bayyinah Ch.4.3", "Use nominal coordination for core phrase; verbal/clause coordination stored separately", "Relation-derived; connector may be attached"),
    ("Badali", "ILMHUB Phrases; ILMHUB Badali explanation", "Store apposition candidates, not all App edges as confirmed Badal", "Teacher review required"),
    ("Four properties of Ism", "ILMHUB Four Properties (DiGNI); Bayyinah Ch.2-3", "Use definiteness, gender, number, I'rab as the course-facing labels", "Direct crosswalk; Bayyinah Ch.3 'qism/type' wording must not silently replace ILMHUB definiteness"),
    ("Frequency-led vocabulary", "85% guide Parts I-III", "Use frequency lists to sequence practice, not as a substitute for grammar; do not reproduce the book's lists", "Method only; copyright restrictions"),
    ("Mudari' mood", "Bayyinah Nahw Ch.7; QAC verb annotation", "Teach Raf'/Nasb/Jazm only on imperfect verbs; Madi and Amr are Mabni", "Traditional grammar safeguard"),
    ("Case system", "Bayyinah Nahw Ch.2; ILMHUB I'raab", "Ism: Raf'/Nasb/Jarr; Fi'l Mudari': Raf'/Nasb/Jazm", "Traditional grammar safeguard"),
]


def jdump(x): return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
def csv_write(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow({k: (jdump(v) if isinstance(v,(dict,list,tuple)) else v) for k,v in r.items()})
def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def loc_tuple(k):
    try:return tuple(int(x) for x in k.split(":"))
    except:return (999,999,999)
def natural_word_key(k): return loc_tuple(k)
def is_definite_word(w):
    segs=w.get("segments",[])
    return any((s.get("pos")=="DET") or str(s.get("features_raw","" )).startswith("PREFIX|al+") for s in segs) or bool(w.get("secondary_db",{}).get("proper_name"))
def get_word_text(words, key, form="indopak"):
    w=words.get(key,{})
    if form=="indopak": return w.get("text_indopak","")
    if form=="normalized": return w.get("text_normalized","")
    if form=="exact": return w.get("text_exact",w.get("text_indopak",""))
    if form=="uthmani": return "".join(s.get("text_uthmani","") for s in w.get("segments",[]) if s.get("text_uthmani"))
    return ""
def get_word_gloss(w):
    for s in w.get("segments",[]):
        if s.get("type")=="STEM" and s.get("gloss"): return s.get("gloss")
    return ""
def get_stem(w):
    return next((s for s in w.get("segments",[]) if s.get("type")=="STEM"),{})
def get_pos(w): return get_stem(w).get("pos","")
def get_word_features(w):
    s=get_stem(w)
    return {k:s.get(k,"") for k in ["case","state","gender","number","aspect","voice","mood","person","verb_form","derived_noun"]}
def map_curriculum(family, sub, source_rel=None):
    if family=="lexical_repeated": return ["X01","F01"]
    if family=="source_constituent":
        return {"PP":["P03","H01"],"NS":["F04","S01"],"VS":["F04","S02"],"CS":["S10"],"SC":["S09"],"S":["F04"]}.get(sub, ["F01"])
    return {
        "idafi":["P02","I01","I04","I05"],
        "tawsifi":["P01","I01","I02","I03","I04"],
        "jarri":["P03","H01","I04"],
        "ishari":["P04","I01"],
        "atfi":["P05","H02","I04"],
        "badali_candidate":["P06","I04"],
        "fa_il":["S02","S03","I04"],
        "maf_ul_bih":["S02","S04","I04"],
        "na_ib_fa_il":["S05","I04"],
        "inna_subject":["S06","I04"], "inna_predicate":["S06","I04"],
        "kana_subject":["S07","I04"], "kana_predicate":["S07","I04"],
        "negation":["S08","H04"], "conditional":["S10","H02"], "conditional_result":["S10"],
        "relative_clause_link":["S09"], "coordination_candidate":["H02"],
        "specification_candidate":["F01"],
    }.get(family,["F01"])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",type=Path,default=DEFAULT_DATA)
    ap.add_argument("--out-dir",type=Path,default=DEFAULT_OUT)
    args=ap.parse_args(); data=args.data_dir; out=args.out_dir; out.mkdir(parents=True,exist_ok=True)
    paths={"words":data/WORD_FILE,"sentences":data/SENT_FILE,"lex":data/LEX_FILE,"lex_exact":data/LEX_EXACT_FILE}
    for k,p in paths.items():
        if not p.exists(): raise FileNotFoundError(f"Missing {k} source: {p}")
    print("Loading whole-word and sentence annotations...", flush=True)
    word_doc=json.load(paths["words"].open(encoding="utf-8")); words=word_doc["words"]
    words_by_ayah=defaultdict(list)
    for wk in words: words_by_ayah[loc_tuple(wk)[:2]].append(wk)
    for ay in words_by_ayah: words_by_ayah[ay].sort(key=natural_word_key)
    sent_doc=json.load(paths["sentences"].open(encoding="utf-8")); sentences=sent_doc["sentences"]
    segment_lookup={seg.get("location"):seg for w in words.values() for seg in w.get("segments",[]) if seg.get("location")}

    occurrences=[]; members=[]; edges=[]; links=[]; review=[]
    counts=Counter(); used_chunk_ids=set()
    def add_chunk(rec, member_rows, concepts):
        cid=rec["chunk_id"]
        if cid in used_chunk_ids: return
        used_chunk_ids.add(cid); occurrences.append(rec); members.extend(member_rows)
        for c in concepts:
            links.append({"chunk_id":cid,"curriculum_concept_id":c,"source_family":rec["chunk_family"],"source_certainty":rec["certainty"]})
        counts[rec["chunk_family"]]+=1
        if rec.get("review_required") in (True,"true","1"):
            review.append({"chunk_id":cid,"chunk_family":rec["chunk_family"],"construction_type":rec["construction_type"],"surah":rec["surah"],"ayahs":rec["ayahs"],"text_indopak":rec["member_text_indopak"],"review_reason":rec["review_reason"],"source_relations":rec["source_relations"]})

    def make_base(cid, family, construction, level, source_type, certainty, sid, word_ids, member_nodes, source_label="", source_relations="", review_required=False, review_reason="", notes=""):
        clean=[]
        for x in word_ids:
            if x and x in words and x not in clean: clean.append(x)
        clean.sort(key=natural_word_key)
        if not clean: return None, []
        suras=sorted({loc_tuple(x)[0] for x in clean}); ayahs=sorted({f"{loc_tuple(x)[0]}:{loc_tuple(x)[1]}" for x in clean},key=lambda z:tuple(map(int,z.split(':'))))
        ind=[get_word_text(words,k,"indopak") for k in clean]
        uth=[get_word_text(words,k,"uthmani") for k in clean]
        norm=[get_word_text(words,k,"normalized") for k in clean]
        first,last=clean[0],clean[-1]
        lo,hi=loc_tuple(first),loc_tuple(last)
        contiguous=(len(clean)==hi[2]-lo[2]+1 and len(suras)==1 and len(ayahs)==1)
        rec={"chunk_id":cid,"chunk_family":family,"construction_type":construction,"chunk_level":level,
             "source_type":source_type,"certainty":certainty,"source_sentence_id":sid,
             "source_label":source_label,"source_relations":source_relations,
             "surah":lo[0],"ayahs":jdump(ayahs),"start_word_id":first,"end_word_id":last,
             "start_word_number":lo[2],"end_word_number":hi[2],"word_count":len(clean),
             "is_contiguous_word_span":contiguous,"crosses_ayah":len(ayahs)>1,
             "member_word_ids":jdump(clean),"member_text_indopak":" ".join(ind),
             "member_text_uthmani":" ".join(x for x in uth if x),"member_text_normalized":" ".join(norm),
             "span_text_indopak":"","span_text_uthmani":"",
             "member_glosses":jdump([get_word_gloss(words[k]) for k in clean]),
             "review_required":bool(review_required),"review_reason":review_reason,"notes":notes}
        # Span text is only populated where the chunk is contiguous in one ayah.
        if contiguous:
            allids=[k for k in words_by_ayah[lo[:2]] if lo[2]<=loc_tuple(k)[2]<=hi[2]]
            rec["span_text_indopak"]=" ".join(get_word_text(words,k,"indopak") for k in allids)
            rec["span_text_uthmani"]=" ".join(get_word_text(words,k,"uthmani") for k in allids if get_word_text(words,k,"uthmani"))
        mrows=[]
        seen=set()
        for idx,m in enumerate(member_nodes):
            key=(m.get("word"),m.get("token_id"),m.get("segment"),m.get("member_role"))
            if key in seen: continue
            seen.add(key)
            wk=m.get("word")
            if not wk or wk not in words: continue
            w=words[wk]; feats=get_word_features(w); sg=segment_lookup.get(m.get("segment",""),{})
            mrows.append({"chunk_id":cid,"member_order":idx+1,"word_id":wk,"segment_id":m.get("segment",""),"token_id":m.get("token_id",""),
                          "member_role":m.get("member_role","member"),"text_indopak":w.get("text_indopak",""),
                          "text_uthmani":get_word_text(words,wk,"uthmani"),"segment_text_uthmani":sg.get("text_uthmani",""),
                          "segment_type":sg.get("type",""),"features_raw":sg.get("features_raw",""),
                          "prefix_tags":jdump(w.get("derived",{}).get("prefix_tags",[])),"suffix_tags":jdump(w.get("derived",{}).get("suffix_tags",[])),
                          "pos":m.get("pos") or get_pos(w),"syntactic_relation":m.get("rel",""),
                          "gloss":get_word_gloss(w),"lemma":(get_stem(w).get("lemma") or {}).get("bw","") if isinstance(get_stem(w).get("lemma"),dict) else "",
                          "root":(get_stem(w).get("root") or {}).get("bw","") if isinstance(get_stem(w).get("root"),dict) else "",
                          **feats})
        return rec,mrows

    # A. Source-defined syntactic constituents. These are not automatically phrase patterns.
    for sid,sent in sentences.items():
        nodes=sent.get("nodes",[]); node_by_id={n.get("token_id"):n for n in nodes}
        for ci,c in enumerate(sent.get("constituents",[]),1):
            tag=c.get("tag",""); word_ids=c.get("words",[])
            if not word_ids: continue
            lo,hi=c.get("token_span",[None,None]); sel=[n for n in nodes if lo is not None and hi is not None and lo<=n.get("token_id",-1)<=hi and n.get("word")]
            # Keep one member record for each word at its first syntactic node in span.
            mn=[]; seenw=set()
            for n in sel:
                if n["word"] not in seenw:
                    seenw.add(n["word"]); mn.append({**n,"member_role":"constituent_member"})
            level={"PP":"phrase","NS":"sentence","VS":"sentence","SC":"clause","CS":"clause","S":"sentence"}.get(tag,"source_span")
            fam="source_constituent"
            construction={"PP":"prepositional_phrase_span","NS":"nominal_sentence_span","VS":"verbal_sentence_span","SC":"subordinate_clause_span","CS":"conditional_sentence_span","S":"sentence_span"}.get(tag,"source_span")
            cid=f"QACC:{sid}:{tag}:{ci}:{word_ids[0]}:{word_ids[-1]}"
            rec,mr=make_base(cid,fam,construction,level,"QAC_treebank_constituent","source_explicit",sid,word_ids,mn,tag)
            if rec:
                rec["source_token_span"]=jdump(c.get("token_span",[])); rec["constituent_source_text"]=c.get("text","")
                add_chunk(rec,mr,map_curriculum(fam,tag))

    # B. Dependency edges. Keep all original edges in a separate audit table; map only targeted relations.
    edge_num=0
    for sid,sent in sentences.items():
        nodes=sent.get("nodes",[]); node_by_id={n.get("token_id"):n for n in nodes}
        word_order={k:i for i,k in enumerate(sent.get("words",[]))}
        for n in nodes:
            rel=n.get("rel",""); head=node_by_id.get(n.get("head"))
            if not head or n.get("head")==n.get("token_id"): continue
            if not n.get("word") or not head.get("word"): continue
            depw, headw=n.get("word"),head.get("word")
            edges.append({"sentence_id":sid,"relation":rel,"relation_ar":n.get("rel_ar",""),"head_token_id":head.get("token_id"),"head_word_id":headw,"head_pos":head.get("pos",""),"head_segment":head.get("segment",""),"dependent_token_id":n.get("token_id"),"dependent_word_id":depw,"dependent_pos":n.get("pos",""),"dependent_segment":n.get("segment",""),"same_written_word":headw==depw,"surah":loc_tuple(depw)[0],"ayah":loc_tuple(depw)[1]})
            if rel not in RELEVANT_RELATIONS: continue
            hp,dp=head.get("pos",""),n.get("pos","")
            family=construction=level="dependency_chunk"; certainty="source_relation"; required=False; reason=""; note=""
            # head is governor; dependent points to its head
            if rel=="Poss":
                family="idafi"; construction="murakkab_idafi_pair"; level="phrase"
                if hp not in NOMINAL_POS or dp not in NOMINAL_POS:
                    family="construct_dependency_candidate"; construction="possessive_relation_candidate"; certainty="pattern_candidate"; required=True; reason="Poss relation endpoints include a non-canonical nominal category; review its phrase status."
                else: certainty="relation_evidence"
                roles={head.get("token_id"):"mudaf",n.get("token_id"):"mudaf_ilayhi"}
            elif rel=="Adj":
                if dp=="ADJ" and hp in NOMINAL_POS:
                    family="tawsifi"; construction="murakkab_tawsifi_pair"; level="phrase"; certainty="relation_evidence"
                else:
                    family="modifier_candidate"; construction="adjectival_or_relative_modifier_candidate"; certainty="pattern_candidate"; required=True; reason="Adj relation is not a direct noun-to-ADJ pair."
                roles={head.get("token_id"):"mawsuf",n.get("token_id"):"sifah_or_modifier"}
            elif rel=="gen" and hp=="P":
                family="jarri"; construction="murakkab_jarri_preposition_governed_ism"; level="phrase"; certainty="relation_evidence"
                roles={head.get("token_id"):"harf_jarr",n.get("token_id"):"ism_majrur"}
                if headw==depw: note="Preposition and governed Ism are separate morphology segments inside one written word."
            elif rel=="conj":
                p1,p2=loc_tuple(headw),loc_tuple(depw)
                between=[x for x in nodes if x.get("pos")=="CONJ" and x.get("word") and (min(p1,p2)<=loc_tuple(x["word"])<=max(p1,p2))]
                connector=bool(between)
                if hp in COORD_NOMINAL_POS and dp in COORD_NOMINAL_POS:
                    family="atfi" if connector else "coordination_candidate"; construction="murakkab_atfi_pair" if connector else "nominal_coordination_candidate"; level="phrase"; certainty="relation_evidence" if connector else "pattern_candidate"
                    if not connector: required=True; reason="Nominal conj dependency found but explicit coordinator node is not within the pair span."
                    roles={head.get("token_id"):"first_conjunct",n.get("token_id"):"second_conjunct"}
                else:
                    family="clause_or_verb_coordination"; construction="coordinated_clause_or_verb"; level="clause"; certainty="source_relation"
                    roles={head.get("token_id"):"first_clause_or_verb",n.get("token_id"):"second_clause_or_verb"}
            elif rel in {"App","Spec"}:
                if hp=="DEM" and dp in {"N","PN"}:
                    target=words.get(depw,{})
                    definite=(dp=="PN") or is_definite_word(target)
                    family="ishari" if definite else "ishari_candidate"
                    construction="murakkab_ishari_demonstrative_plus_definite_ism" if definite else "demonstrative_plus_nondefinite_target_candidate"
                    level="phrase"; certainty="relation_evidence" if definite else "pattern_candidate"
                    required=not definite
                    reason="ILMHUB requires a definite pointed-at noun for the incomplete demonstrative phrase; indefinite target may yield a complete sentence." if not definite else ""
                    roles={head.get("token_id"):"ism_isharah",n.get("token_id"):"mushar_ilayhi"}
                elif rel=="App" and hp in NOMINAL_POS and dp in NOMINAL_POS:
                    family="badali_candidate"; construction="badal_or_apposition_candidate"; level="phrase"; certainty="pattern_candidate"; required=True
                    reason="QAC App relation indicates apposition, but it does not by itself prove the ILMHUB Badali construction; qualified grammar review needed."
                    roles={head.get("token_id"):"mubdal_minhu_candidate",n.get("token_id"):"badal_candidate"}
                elif rel=="Spec":
                    family="specification_candidate"; construction="tamyiz_or_specification_candidate"; level="dependency_chunk"; certainty="pattern_candidate"; required=True
                    reason="QAC Spec is a specification relation, not automatically one of the six ILMHUB phrase constructions."
                    roles={head.get("token_id"):"specified_element",n.get("token_id"):"specification"}
                else:
                    family="apposition_or_specification_candidate"; construction="apposition_or_specification"; level="dependency_chunk"; certainty="pattern_candidate"; required=True
                    reason="Dependency relation alone does not establish one of the six core phrase types."
                    roles={head.get("token_id"):"governor",n.get("token_id"):"dependent"}
            elif rel=="Subj" and hp=="V":
                family="fa_il"; construction="verbal_sentence_agent"; level="sentence_slot"; certainty="source_relation"; roles={head.get("token_id"):"verb",n.get("token_id"):"fa_il"}
                if headw==depw: note="The doer is encoded as an attached/embedded pronoun in the same written word."
            elif rel=="Obj" and hp=="V":
                family="maf_ul_bih"; construction="verbal_sentence_object"; level="sentence_slot"; certainty="source_relation"; roles={head.get("token_id"):"verb",n.get("token_id"):"maf_ul_bih"}
                if headw==depw: note="The object is encoded as an attached pronoun within the written word."
            elif rel=="Pass":
                family="na_ib_fa_il"; construction="passive_subject"; level="sentence_slot"; certainty="source_relation"; roles={head.get("token_id"):"passive_verb",n.get("token_id"):"na_ib_fa_il"}
            elif rel in {"Pred","pred<<in>>","pred <<kan>>","pred<<kan>>"}:
                family="inna_predicate" if "in" in rel else ("kana_predicate" if "kan" in rel else "predicate")
                construction="governed_or_basic_predicate"; level="sentence_slot"; certainty="source_relation"; roles={head.get("token_id"):"governing_particle_or_copula",n.get("token_id"):"khabar_or_predicate"}
            elif rel in {"subj<<in>>","subj <<kan>>"}:
                family="inna_subject" if "in" in rel else "kana_subject"; construction="governed_subject"; level="sentence_slot"; certainty="source_relation"; roles={head.get("token_id"):"governing_particle_or_copula",n.get("token_id"):"ism_inna_or_kana"}
            elif rel=="neg":
                family="negation"; construction="negation_particle_relation"; level="clause"; certainty="source_relation"; roles={head.get("token_id"):"negation_particle",n.get("token_id"):"negated_element"}
            elif rel in {"cond","rslt"}:
                family="conditional" if rel=="cond" else "conditional_result"; construction="conditional_clause_relation"; level="clause"; certainty="source_relation"; roles={head.get("token_id"):"condition_or_link",n.get("token_id"):"condition_clause" if rel=="cond" else "result_clause"}
            elif rel=="sub":
                family="relative_clause_link"; construction="subordinate_or_relative_clause_link"; level="clause"; certainty="source_relation"; roles={head.get("token_id"):"relative_or_subordinating_element",n.get("token_id"):"subordinate_predicate"}
            else: continue

            edge_num+=1
            edge_tokens=[head,n]
            # Coordinator can be an independent node (or prefix) between conjuncts.
            if rel=="conj" and family=="atfi":
                p1,p2=loc_tuple(headw),loc_tuple(depw)
                coord=[x for x in nodes if x.get("pos")=="CONJ" and x.get("word") and min(p1,p2)<=loc_tuple(x["word"])<=max(p1,p2)]
                edge_tokens.extend(coord)
                for x in coord: roles[x.get("token_id")]="harf_atf"
            mid=[]
            for x in edge_tokens:
                xr=dict(x); xr["member_role"]=roles.get(x.get("token_id"),"member"); mid.append(xr)
            word_ids=[x.get("word") for x in edge_tokens if x.get("word")]
            # Extend endpoint range to intermediate written coordinator/member only if within one ayah.
            if len({loc_tuple(w)[:2] for w in word_ids})==1:
                lo=min(loc_tuple(w)[2] for w in word_ids); hi=max(loc_tuple(w)[2] for w in word_ids); ay=loc_tuple(word_ids[0])[:2]
                word_ids=[k for k in sent.get("words",[]) if loc_tuple(k)[:2]==ay and lo<=loc_tuple(k)[2]<=hi]
            cid=f"QACR:{sid}:{rel}:{n.get('token_id')}:{headw}:{depw}"
            rec,mr=make_base(cid,family,construction,level,"QAC_dependency_relation",certainty,sid,word_ids,mid,source_relations=rel,review_required=required,review_reason=reason,notes=note)
            if rec:
                rec["head_word_id"]=headw; rec["dependent_word_id"]=depw; rec["head_pos"]=hp; rec["dependent_pos"]=dp
                rec["same_written_word"]=headw==depw
                add_chunk(rec,mr,map_curriculum(family,construction,rel))

    # C. Repeated lexical n-gram types and occurrences (independent of syntax labels).
    lexical_types=[]; lexical_occ=[]
    def consume_lex(path, match_basis):
        doc=json.load(path.open(encoding="utf-8"))
        for u in doc.get("units",[]):
            n=int(u.get("word_count",0))
            if n<2: continue
            unit_id=f"LEX:{match_basis}:{u['id']}"
            occs=u.get("occurrences",[])
            lexical_types.append({"lexical_chunk_id":unit_id,"source_unit_id":u["id"],"match_basis":match_basis,
                "phrase_normalized":u.get("phrase_normalized",""),"phrase_nastaleeq":u.get("phrase_nastaleeq",""),
                "word_count":n,"total_count":u.get("total_count",len(occs)),"stand_alone_count":u.get("stand_alone_count",0),
                "inside_longer_count":u.get("inside_longer_count",0),"unique_ayah_count":len(u.get("verses_total",[])),
                "ayahs":jdump(u.get("verses_total",[])),"example_start":occs[0].get("start","") if occs else "",
                "example_end":occs[0].get("end","") if occs else "",
                "notes":"Repeated contiguous lexical string; not a grammatical phrase classification."})
            for oi,o in enumerate(occs,1):
                st=o.get("start",""); en=o.get("end","")
                # enumerate ids between endpoints in the same ayah
                sl=loc_tuple(st); el=loc_tuple(en)
                ids=[k for k in words_by_ayah[sl[:2]] if sl[2]<=loc_tuple(k)[2]<=el[2]] if sl[:2]==el[:2] else [st,en]
                ids=sorted(set(ids),key=natural_word_key)
                lexical_occ.append({"lexical_chunk_id":unit_id,"occurrence_number":oi,"match_basis":match_basis,
                    "surah":sl[0],"ayah":sl[1],"start_word_id":st,"end_word_id":en,"word_count":n,
                    "stand_alone":o.get("stand_alone",False),"member_word_ids":jdump(ids),
                    "text_indopak":" ".join(get_word_text(words,k,"indopak") for k in ids),
                    "text_exact":" ".join(get_word_text(words,k,"exact") for k in ids),
                    "text_uthmani":" ".join(get_word_text(words,k,"uthmani") for k in ids if get_word_text(words,k,"uthmani"))})
    consume_lex(paths["lex"],"normalized")
    if paths["lex_exact"].exists(): consume_lex(paths["lex_exact"],"exact_diacritics")

    # D. Type frequencies from grammar-derived chunks.
    type_counter=Counter(); ayah_sets=defaultdict(set); surah_sets=defaultdict(set)
    for r in occurrences:
        key=(r["chunk_family"],r["construction_type"],r["source_type"])
        type_counter[key]+=1; ayah_sets[key].update(json.loads(r["ayahs"])); surah_sets[key].add(r["surah"])
    type_rows=[]
    for key,f in type_counter.most_common():
        type_rows.append({"chunk_family":key[0],"construction_type":key[1],"source_type":key[2],"occurrence_count":f,
            "unique_ayah_count":len(ayah_sets[key]),"unique_surah_count":len(surah_sets[key]),
            "interpretation":"Source-annotated occurrences or relation-derived candidates; not a manual-complete census of all classical grammar phrases."})

    # Exact text-pattern aggregation is useful for finding reusable examples.
    pat_counter=Counter(); pat_ayahs=defaultdict(set); pat_surahs=defaultdict(set); pat_examples={}
    for r in occurrences:
        key=(r["chunk_family"],r["construction_type"],r["member_text_normalized"],r["word_count"])
        pat_counter[key]+=1; pat_ayahs[key].update(json.loads(r["ayahs"])); pat_surahs[key].add(r["surah"])
        pat_examples.setdefault(key, (r["chunk_id"], r["member_text_indopak"], r["member_text_uthmani"], r["start_word_id"]))
    pattern_rows=[]
    for key,f in pat_counter.most_common():
        ex=pat_examples[key]
        pattern_rows.append({"chunk_family":key[0],"construction_type":key[1],"pattern_normalized":key[2],"word_count":key[3],
          "occurrence_count":f,"unique_ayah_count":len(pat_ayahs[key]),"unique_surah_count":len(pat_surahs[key]),
          "example_chunk_id":ex[0],"example_text_indopak":ex[1],"example_text_uthmani":ex[2],"example_location":ex[3]})
    six_defs=[
      ("tawsifi","Murakkab Tawsifi","Relation-derived direct noun-to-ADJ pairs; not manually checked for every edge."),
      ("idafi","Murakkab Idafi","QAC Poss relation; a chain may appear as nested pairs."),
      ("jarri","Murakkab Jarri","QAC gen relation governed by a P node; includes morpheme-only attached prepositions."),
      ("ishari","Murakkab Ishari","DEM to definite N/PN relation only; candidates to indefinite targets excluded."),
      ("atfi","Murakkab Atfi","Nominal conj relation with an explicit CONJ node within the span."),
      ("badali_candidate","Murakkab Badali (candidate)","App relation between nominal endpoints; all records require qualified review before being taught as confirmed Badal."),
    ]
    six_rows=[]
    famcounts=Counter(r["chunk_family"] for r in occurrences)
    for family,label,qualification in six_defs:
        subset=[r for r in occurrences if r["chunk_family"]==family]
        unique_ayah=set()
        for r in subset: unique_ayah.update(json.loads(r["ayahs"]))
        six_rows.append({"ilmhub_construction":label,"chunk_family":family,"observed_count":len(subset),"unique_ayah_count":len(unique_ayah),
          "unique_surah_count":len({r["surah"] for r in subset}),"interpretation_and_qualification":qualification})

    # Nested span hierarchy. This is a location-based containment index, not a claim
    # that two coextensive/overlapping spans have a parent-child grammar relation.
    by_sentence=defaultdict(list)
    for r in occurrences:
        sid=str(r.get("source_sentence_id",""))
        if not sid: continue
        s_words=sentences.get(sid,{}).get("words",[])
        idx={k:i for i,k in enumerate(s_words)}
        mids=json.loads(r["member_word_ids"])
        positions=[idx[k] for k in mids if k in idx]
        if positions:
            by_sentence[sid].append((r,min(positions),max(positions)))
    hierarchy=[]
    for sid,items in by_sentence.items():
        for child,cs,ce in items:
            containers=[]
            for parent,ps,pe in items:
                if parent["chunk_id"]==child["chunk_id"]: continue
                if ps<=cs and pe>=ce and (ps<cs or pe>ce):
                    containers.append((pe-ps,parent["chunk_id"],parent))
            if containers:
                _,pid,parent=min(containers,key=lambda x:x[0])
                hierarchy.append({"parent_chunk_id":pid,"child_chunk_id":child["chunk_id"],
                    "sentence_id":sid,"relation":"span_contains","parent_family":parent["chunk_family"],
                    "child_family":child["chunk_family"],"parent_construction":parent["construction_type"],
                    "child_construction":child["construction_type"]})

    # E. Write outputs.
    occ_fields=["chunk_id","chunk_family","construction_type","chunk_level","source_type","certainty","source_sentence_id","source_label","source_relations","surah","ayahs","start_word_id","end_word_id","start_word_number","end_word_number","word_count","is_contiguous_word_span","crosses_ayah","member_word_ids","member_text_indopak","member_text_uthmani","member_text_normalized","span_text_indopak","span_text_uthmani","member_glosses","source_token_span","constituent_source_text","head_word_id","dependent_word_id","head_pos","dependent_pos","same_written_word","review_required","review_reason","notes"]
    member_fields=["chunk_id","member_order","word_id","segment_id","token_id","member_role","text_indopak","text_uthmani","segment_text_uthmani","segment_type","features_raw","prefix_tags","suffix_tags","pos","syntactic_relation","gloss","lemma","root","case","state","gender","number","aspect","voice","mood","person","verb_form","derived_noun"]
    edge_fields=["sentence_id","relation","relation_ar","head_token_id","head_word_id","head_pos","head_segment","dependent_token_id","dependent_word_id","dependent_pos","dependent_segment","same_written_word","surah","ayah"]
    csv_write(out/"quran_chunk_occurrences.csv",occurrences,occ_fields)
    csv_write(out/"quran_chunk_members.csv",members,member_fields)
    csv_write(out/"quran_dependency_edges.csv",edges,edge_fields)
    csv_write(out/"quran_chunk_curriculum_links.csv",links,["chunk_id","curriculum_concept_id","source_family","source_certainty"])
    csv_write(out/"quran_chunk_hierarchy.csv",hierarchy,["parent_chunk_id","child_chunk_id","sentence_id","relation","parent_family","child_family","parent_construction","child_construction"])
    csv_write(out/"quran_chunk_type_frequency.csv",type_rows,["chunk_family","construction_type","source_type","occurrence_count","unique_ayah_count","unique_surah_count","interpretation"])
    csv_write(out/"grammatical_chunk_pattern_frequency.csv",pattern_rows,["chunk_family","construction_type","pattern_normalized","word_count","occurrence_count","unique_ayah_count","unique_surah_count","example_chunk_id","example_text_indopak","example_text_uthmani","example_location"])
    csv_write(out/"six_core_phrase_pattern_summary.csv",six_rows,["ilmhub_construction","chunk_family","observed_count","unique_ayah_count","unique_surah_count","interpretation_and_qualification"])
    csv_write(out/"repeated_lexical_chunk_types.csv",lexical_types,["lexical_chunk_id","source_unit_id","match_basis","phrase_normalized","phrase_nastaleeq","word_count","total_count","stand_alone_count","inside_longer_count","unique_ayah_count","ayahs","example_start","example_end","notes"])
    csv_write(out/"repeated_lexical_chunk_occurrences.csv",lexical_occ,["lexical_chunk_id","occurrence_number","match_basis","surah","ayah","start_word_id","end_word_id","word_count","stand_alone","member_word_ids","text_indopak","text_exact","text_uthmani"])
    csv_write(out/"curriculum_concept_map.csv",[dict(zip(["curriculum_concept_id","module","concept","learning_use","reference_alignment"],x)) for x in CURRICULUM],["curriculum_concept_id","module","concept","learning_use","reference_alignment"])
    csv_write(out/"source_alignment_audit.csv",[dict(zip(["topic","reference_basis","curriculum_decision","alignment_status"],x)) for x in SOURCE_ALIGNMENT],["topic","reference_basis","curriculum_decision","alignment_status"])
    csv_write(out/"teacher_review_queue.csv",review,["chunk_id","chunk_family","construction_type","surah","ayahs","text_indopak","review_reason","source_relations"])
    summary=[
      {"metric":"whole_word_annotations","value":len(words),"unit":"written word positions","source":WORD_FILE},
      {"metric":"treebank_sentences","value":len(sentences),"unit":"sentence records","source":SENT_FILE},
      {"metric":"grammar_chunk_occurrences","value":len(occurrences),"unit":"constituent + selected dependency occurrences","source":"QAC sentence treebank"},
      {"metric":"grammar_chunk_members","value":len(members),"unit":"member rows","source":"derived from sentence nodes"},
      {"metric":"dependency_edges_exported","value":len(edges),"unit":"non-root dependency rows with overt endpoints","source":SENT_FILE},
      {"metric":"lexical_repeated_chunk_types_normalized","value":sum(1 for x in lexical_types if x['match_basis']=='normalized'),"unit":"repeated n-gram phrase types (2+ words)","source":LEX_FILE},
      {"metric":"lexical_repeated_chunk_types_exact","value":sum(1 for x in lexical_types if x['match_basis']=='exact_diacritics'),"unit":"repeated n-gram phrase types (2+ words)","source":LEX_EXACT_FILE},
      {"metric":"lexical_repeated_chunk_occurrences","value":len(lexical_occ),"unit":"positions across both matching modes","source":"repeated lexical n-gram annotations"},
      {"metric":"distinct_curriculum_links","value":len(links),"unit":"chunk-to-concept links","source":"curriculum crosswalk"},
      {"metric":"strict_chunk_containment_links","value":len(hierarchy),"unit":"nested span links","source":"sentence word order and chunk boundaries"},
      {"metric":"teacher_review_candidates","value":len(review),"unit":"candidate rows requiring review","source":"conservative construction mapping"},
    ]
    for family,count in counts.most_common(): summary.append({"metric":f"grammar_chunk_family:{family}","value":count,"unit":"occurrences","source":"QAC sentence treebank"})
    csv_write(out/"dataset_summary.csv",summary,["metric","value","unit","source"])
    # Data dictionary is short and explicit about units and limits.
    dictionary=[
      ("quran_chunk_occurrences.csv","one row per source constituent or selected dependency-derived teaching chunk","Source constituent, dependency or conservative mapped phrase/role occurrence"),
      ("quran_chunk_members.csv","one row per written-word member within each chunk","Morphology and relation remain source-backed; multiple segments may belong to one written word"),
      ("quran_dependency_edges.csv","one row per overt source dependency edge","Full dependency audit layer, not a list of phrases"),
      ("quran_chunk_curriculum_links.csv","many-to-many chunk-to-curriculum concepts","Concept mapping supports multiple lessons; it does not claim the chunk exemplifies all rules equally"),
      ("quran_chunk_hierarchy.csv","strict span-containment parent/child relations","Location hierarchy only; does not infer grammar from containment"),
      ("quran_chunk_type_frequency.csv","aggregated chunk family/construction/source counts","Counts source-annotated occurrences; not total actual occurrence of all possible phrases"),
      ("grammatical_chunk_pattern_frequency.csv","repeated exact text patterns within a grammar-derived family","Frequency index for retrieval and lesson-example selection; family labels retain their evidence status"),
      ("six_core_phrase_pattern_summary.csv","one summary row per ILMHUB core phrase construction","Badali is explicitly a candidate pending teacher review"),
      ("repeated_lexical_chunk_types.csv","one row per repeated contiguous lexical phrase type, n>=2","Pure repetition inventory; not syntax or semantic classification"),
      ("repeated_lexical_chunk_occurrences.csv","one row per location of a repeated lexical phrase","Normalized and exact-diacritic modes intentionally separate"),
      ("teacher_review_queue.csv","heuristically identified disputed/candidate structures","Not release-ready answer-key annotations"),
    ]
    csv_write(out/"data_dictionary.csv",[dict(zip(["file","row_unit","interpretation"],x)) for x in dictionary],["file","row_unit","interpretation"])
    manifest=[]
    for name,p in paths.items(): manifest.append({"source_key":name,"file_name":p.name,"sha256":sha256(p),"bytes":p.stat().st_size})
    csv_write(out/"source_manifest.csv",manifest,["source_key","file_name","sha256","bytes"])
    print(json.dumps({"words":len(words),"sentences":len(sentences),"grammar_chunks":len(occurrences),"members":len(members),"edges":len(edges),"lexical_types":len(lexical_types),"lexical_occurrences":len(lexical_occ),"review_queue":len(review),"counts":counts},ensure_ascii=False,indent=2,default=dict))

if __name__=="__main__": main()
