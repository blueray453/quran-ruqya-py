#!/usr/bin/env python3
"""Build the narrative DOCX reports using only generated CSV outputs.

This program intentionally does not read the original source datasets. Run the
CSV-generation pipeline first, then point this script at output/csv.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterable

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def read_csv(csv_dir: Path, name: str) -> list[dict]:
    path = csv_dir / name
    if not path.exists():
        raise FileNotFoundError(f'Required CSV not found: {path}. Run the data-generation scripts first.')
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def fmt(value: object) -> str:
    if value is None:
        return ''
    s = str(value)
    try:
        if s.strip() and s.replace(',', '').replace('.', '', 1).isdigit():
            if '.' in s:
                return f'{float(s):,.2f}'.rstrip('0').rstrip('.')
            return f'{int(s):,}'
    except Exception:
        pass
    return s


def set_cell_shading(cell, fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)


def set_repeat_table_header(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'), 'true'); trPr.append(tblHeader)

def prevent_row_split(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    cant = OxmlElement('w:cantSplit'); trPr.append(cant)


def set_cell_margins(cell, top=60, start=75, bottom=60, end=75):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m, v in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = tcMar.find(qn(f'w:{m}'))
        if node is None:
            node = OxmlElement(f'w:{m}'); tcMar.append(node)
        node.set(qn('w:w'), str(v)); node.set(qn('w:type'), 'dxa')


def init_doc(title: str, subtitle: str) -> Document:
    d = Document()
    sec = d.sections[0]
    sec.top_margin = Inches(.68); sec.bottom_margin = Inches(.68)
    sec.left_margin = Inches(.72); sec.right_margin = Inches(.72)
    styles = d.styles
    styles['Normal'].font.name = 'Aptos'; styles['Normal'].font.size = Pt(9)
    styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), 'Aptos')
    for nm, size in [('Title', 24), ('Heading 1', 16), ('Heading 2', 12), ('Heading 3', 10)]:
        st=styles[nm]; st.font.name='Aptos Display'; st.font.size=Pt(size); st.font.color.rgb=RGBColor(28,55,80)
    p=d.add_paragraph(); p.style='Title'; p.alignment=WD_ALIGN_PARAGRAPH.LEFT; p.add_run(title)
    p=d.add_paragraph(); p.paragraph_format.space_after=Pt(4); r=p.add_run(subtitle); r.italic=True; r.font.size=Pt(10); r.font.color.rgb=RGBColor(90,100,110)
    p=d.add_paragraph(); p.paragraph_format.space_after=Pt(12); r=p.add_run(f'Generated {datetime.now(ZoneInfo("Asia/Dhaka")).date().isoformat()} from the CSV outputs in this reproducible project.'); r.font.size=Pt(8); r.font.color.rgb=RGBColor(110,110,110)
    return d


def add_note(doc: Document, text: str):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(7)
    r=p.add_run(text); r.italic=True; r.font.size=Pt(8); r.font.color.rgb=RGBColor(80,90,100)


def add_table(doc: Document, headers: list[str], rows: Iterable[Iterable[object]], max_rows: int | None = None):
    rows=list(rows)
    if max_rows is not None: rows=rows[:max_rows]
    if not headers: return
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    t.autofit=True
    hdr=t.rows[0]; set_repeat_table_header(hdr); prevent_row_split(hdr)
    for i,h in enumerate(headers):
        c=hdr.cells[i]; c.text=str(h).replace('_',' '); set_cell_shading(c,'DCE6F1'); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(c)
        for p in c.paragraphs:
            p.paragraph_format.space_after=Pt(0)
            for r in p.runs: r.bold=True; r.font.size=Pt(7.2)
    for row in rows:
        row_obj=t.add_row(); prevent_row_split(row_obj); cells=row_obj.cells
        for i in range(len(headers)):
            val=row[i] if i<len(row) else ''
            cells[i].text=fmt(val); cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; set_cell_margins(cells[i])
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after=Pt(0); p.paragraph_format.keep_together=True
                for r in p.runs: r.font.size=Pt(7)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t


def add_csv_table(doc, csv_dir, filename, columns=None, max_rows=None, where=None, sort_by=None, descending=False):
    data=read_csv(csv_dir, filename)
    if where: data=[r for r in data if where(r)]
    if sort_by: data.sort(key=lambda r:r.get(sort_by,''), reverse=descending)
    if not data:
        add_note(doc, f'No rows available in {filename}.'); return
    headers=columns or list(data[0].keys())
    add_table(doc, headers, ([r.get(c,'') for c in headers] for r in data), max_rows=max_rows)


def add_bullet(doc, text):
    p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after=Pt(2); p.add_run(text)


def sum_column(rows: list[dict], column: str) -> int:
    total=0
    for r in rows:
        try: total += int(float(r.get(column, 0) or 0))
        except (TypeError, ValueError): pass
    return total


def source_population(csv_dir: Path, source: str, population: str, unit: str | None = None) -> int:
    rows=read_csv(csv_dir,'38_ism_source_population_and_scope.csv')
    for r in rows:
        if r.get('source')==source and r.get('population')==population and (unit is None or r.get('unit')==unit):
            return int(float(r.get('count',0)))
    return 0


def derive_summary_from_csvs(csv_dir: Path) -> dict:
    vocab=read_csv(csv_dir,'17_vocabulary_coverage_summary.csv')
    vocab_by={r['mapping_unit']:r for r in vocab}
    surface_tokens=int(float(vocab_by['surface']['mapped_occurrences']))
    surface_types=int(float(vocab_by['surface']['distinct_terms']))
    qac_stems=sum_column(read_csv(csv_dir,'qac_pos_frequency.csv'),'frequency')
    verb_stems=sum_column(read_csv(csv_dir,'sarf_verb_aspect_frequency.csv'),'frequency')
    imperfect_stems=sum_column(read_csv(csv_dir,'04d_fiil_mood_frequency_imperfect_only.csv'),'frequency')
    roles_total=sum_column(read_csv(csv_dir,'nahw_all_masaq_roles.csv'),'frequency')
    relation_total=sum_column(read_csv(csv_dir,'nahw_relationship_complete_qac.csv'),'frequency')
    constituent_total=sum_column(read_csv(csv_dir,'15_available_source_phrase_span_frequency.csv'),'source_span_count')
    return {
        'surface_tokens':surface_tokens,'surface_types':surface_types,
        'qac_stems':qac_stems,'qac_verb_stems':verb_stems,'qac_imperfect_stems':imperfect_stems,
        'masaq_rows':source_population(csv_dir,'MASAQ CSV (supplied archive)','All annotation rows'),
        'masaq_roles':roles_total,'masaq_ism_stems':source_population(csv_dir,'MASAQ CSV (supplied archive)','Broad Ism stem set','stem segment rows'),
        'qac_relations':relation_total,'qac_constituents':constituent_total,
        'qac_ism_stems':source_population(csv_dir,'QAC morphology 0.4','Broad Ism POS set','stem annotation rows'),
        'qac_ism_words':source_population(csv_dir,'QAC morphology 0.4','Broad Ism POS set','unique word positions'),
    }


def build_main(csv_dir: Path, out: Path):
    d=init_doc('Quranic Arabic: Complete Grammar and Frequency Analysis',
               'Reproducible corpus analysis • Traditional grammar, vocabulary, verbs, Ism, phrase patterns and syntax')
    d.add_heading('1. Executive summary', level=1)
    s=derive_summary_from_csvs(csv_dir)
    add_bullet(d, f"QUL Uthmani word-by-word source: {s['surface_tokens']:,} Quranic word tokens and {s['surface_types']:,} distinct surface forms after excluding numeric verse markers.")
    add_bullet(d, f"QAC morphology v0.4: {s['qac_stems']:,} STEM annotations; {s['qac_verb_stems']:,} verb STEMs, including {s['qac_imperfect_stems']:,} imperfect verbs used as the mood denominator.")
    add_bullet(d, f"Broad QAC Ism pool: {s['qac_ism_stems']:,} Ism-like STEM annotations over {s['qac_ism_words']:,} word positions.")
    add_bullet(d, f"Supplied MASAQ CSV: {s['masaq_rows']:,} data rows, {s['masaq_roles']:,} non-empty word/segment syntactic-role annotations, and {s['masaq_ism_stems']:,} Ism-family STEM rows.")
    add_bullet(d, f"QAC convenience syntax export: {s['qac_relations']:,} observed dependency-relation instances and {s['qac_constituents']:,} constituent annotation rows.")
    add_note(d, 'Counts are source- and unit-specific. QUL word tokens, QAC STEM annotations, QAC convenience-export syntax rows, and MASAQ segments are separate populations; do not pool or add their counts.')

    d.add_heading('2. Vocabulary frequency and coverage', level=1)
    d.add_heading('2.1 Uthmani surface forms', level=2)
    add_csv_table(d,csv_dir,'vocabulary_surface_frequency.csv',columns=['rank','surface_form_uthmani','frequency','pct_of_quranic_word_tokens','cumulative_pct','unique_ayahs','unique_surahs'],max_rows=30)
    d.add_heading('2.2 Lemma, stem and root mapping coverage', level=2)
    add_csv_table(d,csv_dir,'17_vocabulary_coverage_summary.csv')
    add_csv_table(d,csv_dir,'dataset_mapping_coverage.csv',columns=['resource','mapped_occurrences','unique_word_locations','terms_with_occurrences','total_lexicon_terms','terms_without_occurrences','pct_of_quran_tokens_mapped'])
    d.add_heading('2.3 Coverage thresholds', level=2)
    add_csv_table(d,csv_dir,'18_vocabulary_surface_coverage_thresholds.csv')
    for fn,label in [('vocabulary_lemma_frequency.csv','Top lemmas'),('vocabulary_stem_frequency.csv','Top stems'),('vocabulary_root_frequency.csv','Top roots')]:
        d.add_heading(label, level=2)
        first=read_csv(csv_dir,fn)
        cols=list(first[0].keys()) if first else []
        add_csv_table(d,csv_dir,fn,columns=cols[:7],max_rows=25)
    add_note(d, 'Lemma, stem and root denominators are each the mapped occurrences in their respective QUL SQLite resource. These mapping universes differ; percentage columns must not be interpreted as shares of a single common denominator.')

    d.add_heading('3. Verb frequency and morphology', level=1)
    for fn,label in [
        ('sarf_verb_form_frequency.csv','Verb form / wazn'),('sarf_verb_aspect_frequency.csv','Aspect: perfect, imperfect, imperative'),
        ('sarf_verb_voice_frequency.csv','Voice'),('sarf_verb_person_frequency.csv','Person'),
        ('sarf_verb_gender_frequency.csv','Gender'),('sarf_verb_number_frequency.csv','Number'),
        ('04d_fiil_mood_frequency_imperfect_only.csv','Mood of imperfect verbs only')]:
        d.add_heading(label, level=2); add_csv_table(d,csv_dir,fn)
    add_note(d, 'Mood is calculated only over IMPF (Muḍāriʿ) verb STEMs: indicative is the unmarked/default mood within that pool; Māḍī and Amr are not incorrectly assigned indicative mood. Jussive is not a noun case.')
    d.add_heading('3.1 Verb feature bundles', level=2)
    add_csv_table(d,csv_dir,'sarf_verb_feature_bundle_frequency.csv',max_rows=30)
    d.add_heading('3.2 Derived noun forms', level=2)
    add_csv_table(d,csv_dir,'sarf_derived_noun_frequency.csv')

    d.add_heading('4. Ism: complete four-property quantitative profile', level=1)
    add_note(d, f"QAC POS membership is anchored to morphology v0.4, with structured gender/number/case/state features joined from Quranic.csv by exact location. The full STEM-row denominator is {s['qac_ism_stems']:,}; unique word positions are {s['qac_ism_words']:,}.")
    for label,fn in [('Broad Ism POS composition','23_qac_ism_pos_distribution.csv'),('Gender','24_qac_ism_gender_distribution.csv'),('Number','24_qac_ism_number_distribution.csv'),('Case / Iʿrab','24_qac_ism_case_distribution.csv'),('Nominal state / explicit indefiniteness','24_qac_ism_definiteness_state_distribution.csv')]:
        d.add_heading(label, level=2)
        add_csv_table(d,csv_dir,fn,where=lambda r: ('QAC_POS_or_ALL' not in r or r.get('QAC_POS_or_ALL')=='ALL_ISM'))
    d.add_heading('Definiteness evidence by unique word position', level=2)
    add_csv_table(d,csv_dir,'27_qac_ism_definiteness_evidence_distribution.csv')
    d.add_heading('Feature annotation coverage', level=2)
    add_csv_table(d,csv_dir,'42_qac_ism_feature_annotation_coverage.csv')
    d.add_heading('Ism subtype families in supplied MASAQ CSV', level=2)
    add_csv_table(d,csv_dir,'31_masaq_ism_family_distribution.csv')
    for fn,label in [('32_masaq_ism_declineability_labels.csv','Declinability / invariable labels'),('33_masaq_ism_case_mood_labels.csv','MASAQ case/mood source labels'),('34_masaq_ism_case_marker_labels.csv','MASAQ case-marker labels'),('35_masaq_ism_possessive_construct.csv','Possessive construct labels')]:
        d.add_heading(label, level=2); add_csv_table(d,csv_dir,fn)
    add_note(d, 'Unmarked is an annotation gap, not a grammatical category. Definiteness is presented as explicit INDEF plus positive marker/evidence and unresolved counts; no false binary is inferred. MASAQ JUSSIVE and SUKUN source labels are retained for audit, not taught as fourth noun case or a separate case.')

    d.add_heading('5. Traditional grammar architecture', level=1)
    add_note(d, 'The complete 90-topic architecture is preserved below as a full curriculum map. Frequency status indicates where corpus frequency is measurable versus where instruction is organised by conceptual prerequisites.')
    add_csv_table(d,csv_dir,'10_traditional_grammar_architecture.csv')
    d.add_heading('5.1 Four properties of Ism: complete taxonomy', level=2)
    add_csv_table(d,csv_dir,'11_ism_four_properties_complete_taxonomy.csv')
    d.add_heading('5.2 Verb properties reference', level=2)
    add_csv_table(d,csv_dir,'04c_fiil_property_reference.csv')

    d.add_heading('6. Phrase constructions and syntactic function', level=1)
    d.add_heading('6.1 Six learner-facing phrase construction patterns', level=2)
    add_csv_table(d,csv_dir,'13_phrase_construction_taxonomy.csv')
    add_note(d, 'The six construction patterns describe a phrase’s internal build. They are not the same as the source Phrasal_Function categories that describe the phrase’s external syntactic job.')
    d.add_heading('6.2 MASAQ phrase-function taxonomy', level=2)
    add_csv_table(d,csv_dir,'14_phrase_function_taxonomy_masaq.csv')
    d.add_heading('6.3 Available QAC constituent-span labels', level=2)
    add_csv_table(d,csv_dir,'15_available_source_phrase_span_frequency.csv')
    add_note(d, 'These are rows in the supplied QAC.csv constituent annotations, not reconstructed MASAQ phrase instances and not counts of the six learner-facing constructions.')
    d.add_heading('6.4 MASAQ word/segment-level syntactic roles', level=2)
    add_csv_table(d,csv_dir,'01d_masaq_word_role_frequency_not_phrase_function.csv',max_rows=35)
    add_note(d, 'MASAQ role values are word/segment annotations. They are not phrase-span Phrasal_Function counts; summing member-word roles would inflate phrase frequencies.')
    d.add_heading('6.5 Dependency relations', level=2)
    add_csv_table(d,csv_dir,'nahw_relationship_complete_qac.csv',max_rows=40)

    d.add_heading('7. Method, sources, quality controls and licensing', level=1)
    add_csv_table(d,csv_dir,'22_sources_provenance_and_licensing.csv')
    add_csv_table(d,csv_dir,'00_delivery_status.csv')
    for text in [
        'QAC morphology v0.4 uses the supplied source POS and morphology tags. Its source file contains an attribution and GNU GPL notice that must remain with the corpus and any substantial derivative use.',
        'The QAC extended Quranic.csv convenience export is kept separate from raw QAC morphology v0.4. Its structured POS fields can differ; for Ism distributions, raw v0.4 establishes membership and the convenience export supplies the joined structured features.',
        'The supplied MASAQ CSV has 157,676 data rows, which does not match the 131,930 morpheme-entry profile described in the associated research article. It is explicitly labelled as the supplied archive CSV, not an independently verified V6 snapshot. The Mendeley V6 record lists CC BY-NC 3.0; verify provenance and rights before commercial use.',
        'QUL resources have resource-specific reuse terms. This project preserves the supplied WBW and SQLite files; check current QUL terms before redistributing the source data or using it commercially.',
        'Tanzil text-derived material must retain its attribution and the source terms included in the supplied text where applicable. Do not alter the source text or remove its notices.',
        'The Arabic101 85% book and Bayyinah source PDF are intentionally not included in the data-source archive. The supplied Arabic101 copy was marked personal-use-only; the project uses curriculum maps and references rather than redistributing book contents.',
        'This is a reproducible statistical and pedagogical research pipeline, not a substitute for expert Arabic grammar review. Human review is required for ambiguous POS, iʿrāb, nested/discontinuous phrase boundaries, and disputed interpretations.'
    ]: add_bullet(d,text)
    add_note(d, 'For executable reproduction commands and exact file provenance, see README.md and SOURCES_AND_LICENSES.md in the project root.')
    out.parent.mkdir(parents=True,exist_ok=True); d.save(out)


def build_ism(csv_dir: Path, out: Path):
    d=init_doc('Quantitative Ism Feature Distributions',
               'Quran-wide distributions of definiteness, gender, number, Iʿrab/case, plus MASAQ morphology diagnostics')
    d.add_heading('1. Population and counting unit',level=1)
    q_all=source_population(csv_dir,'QAC morphology 0.4','All STEM rows','stem annotation rows')
    q_ism=source_population(csv_dir,'QAC morphology 0.4','Broad Ism POS set','stem annotation rows')
    q_words=source_population(csv_dir,'QAC morphology 0.4','Broad Ism POS set','unique word positions')
    m_all=source_population(csv_dir,'MASAQ CSV (supplied archive)','All Stem rows','stem segment rows')
    m_ism=source_population(csv_dir,'MASAQ CSV (supplied archive)','Broad Ism stem set','stem segment rows')
    m_words=source_population(csv_dir,'MASAQ CSV (supplied archive)','Broad Ism stem set','unique word positions')
    add_bullet(d,f"QAC morphology v0.4: {q_all:,} total STEM annotations; broad Ism set {q_ism:,} STEM annotations over {q_words:,} word positions.")
    add_bullet(d,f"Supplied MASAQ CSV: {m_all:,} STEM segment rows; {m_ism:,} Ism-family STEM rows over {m_words:,} unique word positions.")
    add_note(d,'QAC and MASAQ use different tagsets, segmentation and annotation populations. Their counts are reported separately and are not added together.')
    for title,filename in [
        ('QAC Ism POS composition','23_qac_ism_pos_distribution.csv'),
        ('Gender distribution','24_qac_ism_gender_distribution.csv'),
        ('Number distribution','24_qac_ism_number_distribution.csv'),
        ('Case / Iʿrab distribution','24_qac_ism_case_distribution.csv'),
        ('Explicit nominal state distribution','24_qac_ism_definiteness_state_distribution.csv')]:
        d.add_heading(title,level=1)
        add_csv_table(d,csv_dir,filename,where=lambda r: ('QAC_POS_or_ALL' not in r or r.get('QAC_POS_or_ALL')=='ALL_ISM'))
    d.add_heading('Definiteness evidence',level=1); add_csv_table(d,csv_dir,'27_qac_ism_definiteness_evidence_distribution.csv')
    d.add_heading('Definiteness marker overlap diagnostics',level=1); add_csv_table(d,csv_dir,'28_qac_ism_definiteness_marker_overlap.csv')
    d.add_heading('Gender and number marked subsets',level=1)
    add_csv_table(d,csv_dir,'25_qac_ism_gender_marked_subset.csv'); add_csv_table(d,csv_dir,'25_qac_ism_number_marked_subset.csv')
    d.add_heading('Feature annotation coverage',level=1); add_csv_table(d,csv_dir,'42_qac_ism_feature_annotation_coverage.csv')
    d.add_heading('MASAQ Ism family composition',level=1); add_csv_table(d,csv_dir,'31_masaq_ism_family_distribution.csv')
    for fn,label in [('32_masaq_ism_declineability_labels.csv','Declinability / invariable labels'),('33_masaq_ism_case_mood_labels.csv','Case_Mood'),('34_masaq_ism_case_marker_labels.csv','Case_Mood_Marker'),('35_masaq_ism_possessive_construct.csv','Possessive_Construct')]:
        d.add_heading(label,level=1); add_csv_table(d,csv_dir,fn)
    for fn,label in [('36_masaq_ism_family_by_declinability.csv','Ism family by declinability'),('36_masaq_ism_family_by_case_mood.csv','Ism family by Case_Mood'),('36_masaq_ism_family_by_possessive_construct.csv','Ism family by construct status'),('40_masaq_ism_family_by_case_marker.csv','Ism family by case marker')]:
        d.add_heading(label,level=1); add_csv_table(d,csv_dir,fn)
    d.add_heading('Data quality and interpretation rules',level=1)
    for text in [
        'QAC Ism membership is defined by POS tags N, PN, ADJ, T, LOC, PRON, REL and DEM. It is a broad learner-facing Ism-like pool; core common/proper nouns are available as separate POS rows.',
        'The QAC Ism POS denominator is 40,778 STEM annotations, but five word positions have two Ism STEM analyses. Most feature tables count STEM annotations; definiteness evidence is counted once per unique word position.',
        'Gender: M and F are explicit; UNMARKED is retained. Number: S, D and P are explicit; UNMARKED is retained. Never infer the missing value as masculine or singular.',
        'Case: NOM, ACC and GEN are the three noun case states. Unmarked remains separate. Jussive is a verb mood, not a noun case; Sukoon is a sign/marker, not another noun case.',
        'QAC morphology v0.4 does not provide a complete DEF/INDEF state pair. INDEF is explicit for a subset. Definiteness is therefore reported using positive evidence categories and unresolved counts, not as a false binary.',
        'The MASAQ family tags group common/proper/derived nouns, verbal nouns, pronouns/demonstratives/relatives/interrogatives, adjectives and adverbial nouns. Raw labels remain visible in CSVs.',
        'The supplied MASAQ CSV contains 157,676 rows and its counts do not fully reconcile to the article profile. The results describe this archive file pending independent version reconciliation. Verify provenance and licence before redistribution/commercial use.'
    ]: add_bullet(d,text)
    out.parent.mkdir(parents=True,exist_ok=True); d.save(out)


def main():
    ap=argparse.ArgumentParser(description='Build narrative DOCX reports from generated CSVs only.')
    ap.add_argument('--csv-dir',required=True,help='Directory containing generated CSV outputs')
    ap.add_argument('--output-dir',required=True,help='Report output directory')
    a=ap.parse_args(); c=Path(a.csv_dir); o=Path(a.output_dir); o.mkdir(parents=True,exist_ok=True)
    build_main(c,o/'complete_analysis_report.docx')
    build_ism(c,o/'quantitative_ism_report.docx')
    print(json.dumps({'complete_report':str(o/'complete_analysis_report.docx'),'ism_report':str(o/'quantitative_ism_report.docx'),'input':'CSV directory only'},indent=2))

if __name__=='__main__': main()
