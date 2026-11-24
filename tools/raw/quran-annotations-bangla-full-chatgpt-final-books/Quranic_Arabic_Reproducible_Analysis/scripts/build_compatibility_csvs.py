#!/usr/bin/env python3
"""Build compatibility/status/provenance CSVs after core + Ism CSV generation."""
import argparse, csv, json
from pathlib import Path


def readcsv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def writecsv(p,headers,rows):
    with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)

def as_int(x):
    try:return int(float(x))
    except:return 0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--csv-dir',required=True);ap.add_argument('--data-dir',required=True)
    a=ap.parse_args(); C=Path(a.csv_dir); D=Path(a.data_dir)
    # Convert the new raw QAC Ism feature tables into the original report's compatibility views.
    case=readcsv(C/'29_qac_ism_case_distribution_summary.csv')
    rows=[]; marked=sum(as_int(r['frequency']) for r in case if r['case_state'] in {'GEN','ACC','NOM'})
    cum=0
    for rank,r in enumerate(sorted([x for x in case if as_int(x['frequency'])>0],key=lambda x:-as_int(x['frequency'])),1):
        n=as_int(r['frequency']); cum+=n
        rows.append([rank,r['case_state'],n,round(n/marked*100,6) if marked else 0,cum,round(cum/marked*100,6) if marked else 0])
    writecsv(C/'qac_nominal_case_frequency.csv',['rank','nominal_case','frequency','percentage','cumulative_frequency','cumulative_percentage'],
             [[r[0],r[1],r[2],r[3],r[4],r[5]] for r in rows if r[1] in {'GEN','ACC','NOM'}])
    state=readcsv(C/'24_qac_ism_definiteness_state_distribution.csv')
    st=[r for r in state if r['QAC_POS_or_ALL']=='ALL_ISM' and r['feature_value']!='UNMARKED']
    tot=sum(as_int(r['frequency']) for r in st); out=[]; cum=0
    for rank,r in enumerate(sorted(st,key=lambda x:-as_int(x['frequency'])),1):
        n=as_int(r['frequency']);cum+=n
        out.append([rank,r['feature_value'],n,round(n/tot*100,6) if tot else 0,cum,round(cum/tot*100,6) if tot else 0])
    writecsv(C/'qac_nominal_state_frequency.csv',['rank','nominal_state','frequency','percentage','cumulative_frequency','cumulative_percentage'],out)
    # Cross-check style table; all three noun cases are reported from QAC raw morphology 0.4.
    writecsv(C/'02c_ism_case_frequency_qac_crosscheck_only.csv',
      ['rank','case_state','arabic_term','english_label','frequency','percentage_of_case_marked_subset','denominator','source','warning'],
      [[r[0],r[1],{'GEN':'جر','ACC':'نصب','NOM':'رفع'}.get(r[1],''),{'GEN':'Genitive / Majrur','ACC':'Accusative / Mansub','NOM':'Nominative / Marfuʿ'}.get(r[1],''),r[2],r[3],marked,'QAC morphology v0.4 raw text','Denominator includes only case-marked Ism STEM annotations; separate from MASAQ.'] for r in rows if r[1] in {'GEN','ACC','NOM'}])
    # Legacy partial-state table updated to make the limits explicit.
    indef=next((as_int(r['frequency']) for r in state if r['QAC_POS_or_ALL']=='ALL_ISM' and r['feature_value']=='INDEF'),0)
    all_ism=next((as_int(r['denominator']) for r in state if r['QAC_POS_or_ALL']=='ALL_ISM'),0)
    writecsv(C/'02d_ism_definiteness_qac_partial_only.csv',['source','value','frequency','denominator','percentage','status','interpretation'],[
      ['QAC morphology v0.4','INDEF',indef,all_ism,round(indef/all_ism*100,6) if all_ism else 0,'PARTIAL_ONLY','No explicit DEF feature in this export; unmarked values are not automatically definite or indefinite.']])
    # Status of the four traditional Ism properties, drawn from generated Ism CSVs.
    gender=readcsv(C/'24_qac_ism_gender_distribution.csv'); number=readcsv(C/'24_qac_ism_number_distribution.csv')
    state=readcsv(C/'24_qac_ism_definiteness_state_distribution.csv')
    props=[]
    for prop,table,code_col,val_map in [
      ('Gender',gender,'feature_value',{'M':'Masculine','F':'Feminine','UNMARKED':'Unmarked'}),
      ('Number',number,'feature_value',{'S':'Singular','D':'Dual','P':'Plural','UNMARKED':'Unmarked'}),
      ('Definiteness',state,'feature_value',{'INDEF':'Explicit indefinite','UNMARKED':'State not explicit'})]:
        for r in table:
            if r['QAC_POS_or_ALL']!='ALL_ISM':continue
            val=r['feature_value']; n=as_int(r['frequency'])
            props.append([prop,val_map.get(val,val),n,r['pct_within_denominator'],r['denominator'],'QAC morphology v0.4','AVAILABLE_WITH_UNMARKED_GAPS' if val=='UNMARKED' else 'MEASURED','Unmarked is not a grammatical value; percentages use the broad QAC Ism STEM denominator.'])
    for r in case:
        if r['case_state']!='ALL_ISM':
            props.append(["I‘rab / case",{'GEN':'Majrur','ACC':'Mansub','NOM':'Marfuʿ','UNMARKED':'No explicit case'}.get(r['case_state'],r['case_state']),as_int(r['frequency']),r['pct_of_all_Ism_stem_rows'],r['all_Ism_denominator'],'QAC morphology v0.4','AVAILABLE_WITH_UNMARKED_GAPS','Only Rafʿ, Nasb and Jarr are noun cases; unmarked retained.'])
    writecsv(C/'12_ism_property_frequency_status.csv',['property','value_label','frequency','percentage_of_broad_Ism_STEM_rows','denominator','source','status','interpretation'],props)
    # Feature gaps / coverage summary.
    coverage=readcsv(C/'42_qac_ism_feature_annotation_coverage.csv')
    writecsv(C/'20_ism_feature_frequency_gaps.csv',['property','required_values','source_fields_expected','frequency_status','available_count','available_denominator','notes'],[
      ['Gender','Mudhakkar / Mu’annath','Gender','Measured with explicit M/F plus unmarked',next((r['rows_with_explicit_feature'] for r in coverage if r['property']=='Gender'),''),next((r['denominator'] for r in coverage if r['property']=='Gender'),''),'Keep unmarked separate; do not infer masculine.'],
      ['Number','Mufrad / Muthanna / Jamʿ','Number','Measured with S/D/P plus unmarked',next((r['rows_with_explicit_feature'] for r in coverage if r['property']=='Number'),''),next((r['denominator'] for r in coverage if r['property']=='Number'),''),'Plural subtype (sound masculine, sound feminine, broken plural) is not fully resolved by the aggregate code.'],
      ['Definiteness','Maʿrifah / Nakirah','INDEF plus Al- / PN / PRON / REL / DEM / suffix evidence','Evidence classes; not a complete source DEF/INDEF pair',indef,all_ism,'Positive evidence and explicit INDEF are retained; residual records are unresolved.'],
      ["Iʿrab / case",'Rafʿ / Nasb / Jarr','NOM / ACC / GEN','Measured with unmarked state',marked,all_ism,'Visible signs and estimated case are separate from syntactic case state.']])
    # Phrase-frequency status: raw MASAQ rows are now present; true span reconstruction remains an additional algorithm/review stage.
    writecsv(C/'19_phrase_frequency_data_status.csv',['analysis','status','available','required','valid_counting_unit'],[
      ['Six teaching phrase-pattern rankings','NOT_YET_RECONSTRUCTED','Construction taxonomy and QAC constituent labels are available.','Map each distinct phrase span to one of the six learner constructions; resolve ambiguous patterns.','Distinct phrase span instances; nested spans separately.'],
      ['MASAQ Phrase span-type frequency','SOURCE_AVAILABLE_SPANS_NOT_RECONSTRUCTED','Raw MASAQ.csv is bundled and contains Phrase / Phrasal_Function fields.','Reconstruct start/end boundaries from V6 row ordering and codebook; verify discontinuous and nested spans.','Distinct Phrase instance IDs, not member-word rows.'],
      ['MASAQ Phrasal_Function frequency','SOURCE_AVAILABLE_SPANS_NOT_RECONSTRUCTED','Raw MASAQ.csv includes Phrasal_Function on segment rows.','Resolve one external function per reconstructed phrase span; preserve multiple functions only when supported.','Distinct phrase spans by external function.'],
      ['QAC constituent annotation frequency','AVAILABLE_SOURCE_LABEL_COUNTS','Quranic.csv constituent_label annotations counted directly.','Reconcile the QAC convenience export release and span definitions before mapping to learner phrase types.','Source constituent annotation rows.']])
    # Source information; provenance differences must remain visible.
    writecsv(C/'22_sources_provenance_and_licensing.csv',['source','purpose','version_or_scope','url','status_or_license_note'],[
      ['QUL WBW + lemma/stem/root SQLite maps','Surface, lemma, stem and root frequency','uthmani-wbw.json; word-lemma.db / word-stem.db / word-root.db','https://qul.tarteel.ai/resources','The archive preserves the supplied source data; confirm per-resource reuse terms before redistribution.'],
      ['QAC morphology v0.4','POS, verb features, Ism properties','quranic-corpus-morphology-0.4.txt','https://corpus.quran.com/documentation/morphologicalfeatures.jsp','Source file identifies GPL terms and copyright notice; preserve source attribution and license.'],
      ['QAC extended convenience export','Dependency relations and constituent annotations','Quranic.csv, UTF-16 TSV export','https://corpus.quran.com/','Counts are tied to the supplied export. Convenience export POS fields can differ from raw v0.4 morphology; this report keeps them separate.'],
      ['MASAQ supplied CSV','Syntactic roles, Ism subtype and morphology fields','MASAQ.csv; 157,676 rows in supplied archive','https://data.mendeley.com/datasets/9yvrzxktmr/6','Supplied CSV does not fully reconcile to published article profile; do not assume exact V6 snapshot. Mendeley V6 record lists CC BY-NC 3.0; verify provenance and terms.'],
      ['ILMHUB grammar references','Traditional Ism, phrase and grammar taxonomy','Pages consulted to structure teaching taxonomy','https://www.ilmhub.org/arabic-grammar/','Reference only; author original instructional content and verify permissions.'],
      ['Arabic101 85% book','Vocabulary prioritisation context','User-supplied copy marked personal use only','https://store.arabic101.org/85landing/','Not included in this source bundle; do not copy or redistribute its contents.']])
    # Current delivery status.
    writecsv(C/'00_delivery_status.csv',['analysis_area','status','generated_outputs','limitations'],[
      ['Traditional grammar architecture','GENERATED','10_traditional_grammar_architecture.csv; 11_ism_four_properties_complete_taxonomy.csv','Teaching taxonomy is comprehensive, but expert review of disputed analyses remains required.'],
      ['Vocabulary frequency','GENERATED_FROM_RAW_SOURCE','vocabulary_surface_frequency.csv; vocabulary_lemma_frequency.csv; vocabulary_stem_frequency.csv; vocabulary_root_frequency.csv; coverage tables','QUL source positions do not perfectly align to QAC/MASAQ.'],
      ['Verb feature frequency','GENERATED_FROM_QAC_V0_4','sarf_verb_*_frequency.csv; 04d_fiil_mood_frequency_imperfect_only.csv','Mood is calculated only over imperfect verbs.'],
      ['Ism feature distributions','GENERATED_WITH_ANNOTATION_GAPS','22-42 QAC/MASAQ Ism CSVs; 12_ism_property_frequency_status.csv','Unmarked feature values are retained; full definiteness binary cannot be inferred from source tags alone.'],
      ['Phrase construction and function','TAXONOMY_COMPLETE_FREQUENCY_PARTIAL','01a-01c and 13-15, 19 CSVs','QAC constituent counts and MASAQ word roles are not MASAQ phrase-span/function frequencies.']])
    # Report README.
    readme='''QURANIC ARABIC ANALYSIS - GENERATED CSV OUTPUTS\n\nAll CSV files in this directory are generated or copied as clearly identified reference/taxonomy tables by run_pipeline.py. Frequency tables are rebuilt from the source files bundled in data_sources.zip. Hand-curated curriculum taxonomies and output templates are copied from reference_tables.zip.\n\nImportant units:\n- QUL surface frequency counts WBW word positions after removing numeric verse markers.\n- QUL lemma/stem/root mappings use their independent SQLite mapping records and denominators.\n- QAC morphology v0.4 supplies POS, verb features and Ism feature distributions.\n- QAC Quranic.csv supplies dependency relationship and constituent annotation counts.\n- MASAQ.csv supplied archive drives word/segment syntactic roles and MASAQ Ism family tables. It is not merged with QAC.\n- Ism unmarked values remain unmarked; no automatic defaults are invented.\n- Imperfect-verb mood uses only Muḍāriʿ occurrences. Māḍī and Amr are not assigned Indicative mood.\n- The six teaching phrase patterns and the eight phrase-function families are different dimensions. QAC constituent labels and MASAQ word roles are not phrase-span/function counts.\n\nFor all methods, source versions and rights cautions, read ../README.md and ../SOURCES_AND_LICENSES.md.\n'''
    (C/'README_COMPLETE_ANALYSIS.txt').write_text(readme,encoding='utf-8')
    # Top-level machine-readable source + CSV profile
    freq=json.loads((C/'frequency_build_summary.json').read_text(encoding='utf-8'))
    ism=json.loads((C/'summary.json').read_text(encoding='utf-8'))
    (C/'reproduction_summary.json').write_text(json.dumps({'frequency':freq,'ism':ism},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Compatibility, status, provenance tables generated.')

if __name__=='__main__':main()
