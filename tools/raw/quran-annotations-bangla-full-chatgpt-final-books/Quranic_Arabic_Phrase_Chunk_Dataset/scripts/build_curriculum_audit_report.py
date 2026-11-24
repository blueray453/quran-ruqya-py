#!/usr/bin/env python3
"""Build the curriculum audit and dataset report using generated CSV outputs only."""
import argparse, csv, json
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
def readcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def set_cell_shading(cell, fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)
def set_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr(); tblHeader=OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'),'true'); trPr.append(tblHeader)
def add_page_num(paragraph):
    run=paragraph.add_run(); fldChar1=OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'),'begin')
    instr=OxmlElement('w:instrText'); instr.set(qn('xml:space'),'preserve'); instr.text=' PAGE '
    fldChar2=OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'),'end')
    run._r.append(fldChar1); run._r.append(instr); run._r.append(fldChar2)
def add_table(doc, headers, rows, widths=None, font_size=8):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Light Shading Accent 1'
    hdr=t.rows[0]; set_repeat_table_header(hdr)
    for row in t.rows:
        trPr=row._tr.get_or_add_trPr(); cant=OxmlElement('w:cantSplit'); trPr.append(cant)
    for i,h in enumerate(headers):
        c=hdr.cells[i]; c.text=str(h); set_cell_shading(c,'D9EAF7')
        for p in c.paragraphs:
            for r in p.runs:r.bold=True; r.font.size=Pt(font_size)
    for row in rows:
        tr=t.add_row()
        trPr=tr._tr.get_or_add_trPr(); cant=OxmlElement('w:cantSplit'); trPr.append(cant)
        cells=tr.cells
        for i,v in enumerate(row):
            cells[i].text=str(v if v is not None else '')
            cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after=Pt(1)
                for r in p.runs:r.font.size=Pt(font_size)
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t
def bullet(doc,text):
    p=doc.add_paragraph(style='List Bullet'); p.add_run(text); return p
def note(doc,text):
    p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(.18); p.paragraph_format.right_indent=Inches(.18)
    r=p.add_run(text); r.italic=True; r.font.size=Pt(9); r.font.color.rgb=RGBColor(80,80,80)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--csv-dir',type=Path,default=ROOT/'output/csv'); ap.add_argument('--output',type=Path,default=ROOT/'output/reports/curriculum_alignment_and_chunk_dataset.docx'); args=ap.parse_args()
    csvdir=args.csv_dir; args.output.parent.mkdir(parents=True,exist_ok=True)
    summary={r['metric']:int(r['value']) for r in readcsv(csvdir/'dataset_summary.csv')}
    six=readcsv(csvdir/'six_core_phrase_pattern_summary.csv')
    freq=readcsv(csvdir/'quran_chunk_type_frequency.csv')
    source_const=[r for r in freq if r['source_type']=='QAC_treebank_constituent']
    role_names={
      'fa_il':'Fa\'il / agent','maf_ul_bih':'Maf\'ul bih / object','na_ib_fa_il':'Na\'ib al-Fa\'il',
      'inna_subject':'Ism Inna','inna_predicate':'Khabar Inna','kana_subject':'Ism Kana','kana_predicate':'Khabar Kana',
      'negation':'Negation relation','relative_clause_link':'Relative/subordinate clause link','conditional':'Condition relation','conditional_result':'Result relation'
    }
    role_rows=[]
    for fam,label in role_names.items():
        r=next((x for x in freq if x['chunk_family']==fam),None)
        if r: role_rows.append((label,r['occurrence_count'],r['unique_ayah_count'],r['unique_surah_count']))
    doc=Document(); sec=doc.sections[0]; sec.top_margin=Inches(.65); sec.bottom_margin=Inches(.65); sec.left_margin=Inches(.7); sec.right_margin=Inches(.7)
    styles=doc.styles; styles['Normal'].font.name='Aptos'; styles['Normal'].font.size=Pt(9)
    for sn,size,color in [('Title',25,'183B56'),('Heading 1',16,'183B56'),('Heading 2',12,'285F82')]:
        st=styles[sn]; st.font.name='Aptos Display'; st.font.size=Pt(size); st.font.color.rgb=RGBColor.from_string(color)
    header=sec.header.paragraphs[0]; header.text='QURANIC ARABIC | CURRICULUM ALIGNMENT & CHUNK DATASET'; header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor(90,100,110)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT; footer.add_run('Research dataset | page '); add_page_num(footer)

    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('Quran-wide Phrase & Chunk Dataset'); r.bold=True; r.font.size=Pt(25); r.font.color.rgb=RGBColor(24,59,86)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('Curriculum alignment, source audit, extraction method and dataset guide'); r.font.size=Pt(12); r.font.color.rgb=RGBColor(80,92,105)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Prepared from supplied Bayyinah / Arabic101 references, ILMHUB framework and QAC-based annotations').italic=True

    doc.add_heading('1. Executive decision: stay with the established teaching spine',1)
    doc.add_paragraph('The curriculum should not be reorganised around a new computational taxonomy. Keep the learner-facing sequence that is already present in the references: word classes, the Ism properties, phrase construction, sentence type and sentence roles, then longer clauses and ayah comprehension. The new dataset is an evidence and practice layer supporting that sequence; it is not a replacement grammar syllabus.')
    bullet(doc,'ILMHUB Foundations supplies the 3–2–6 frame: three word classes (Ism, Fi\'l, Harf), two principal sentence types (nominal and verbal), and six common phrase constructions.')
    bullet(doc,'Bayyinah Nahw Section 1 develops these same ideas through I\'rab, Jarr/Idafah, gender/number/type, descriptive and demonstrative structures, conjunction, nominal sentences, past and imperfect verbs, passive voice, negation, Kana-type verbs and compound Ism constructions.')
    bullet(doc,'The frequency guide supports vocabulary sequencing and review; use its method only. Its supplied copy is marked personal-use-only and not for sale/distribution, so this project does not reproduce its vocabulary lists or explanatory pages.')
    note(doc,'Curriculum rule: introduce the traditional learner-facing concept first; let the corpus supply examples, frequency and practice candidates. Do not teach a source annotation label as a grammar rule without review.')

    doc.add_heading('2. Curriculum audit against the supplied books and ILMHUB',1)
    audit=readcsv(csvdir/'source_alignment_audit.csv')
    rows=[]
    for x in audit:
        rows.append((x['topic'],x['reference_basis'],x['curriculum_decision'],x['alignment_status']))
    add_table(doc,['Topic','Reference basis','Decision for our curriculum','Status'],rows,[1.3,1.55,2.55,1.0],7)

    doc.add_heading('2.1 Book-level sequence retained',2)
    book_rows=[
      ('Bayyinah Nahw Ch.1','Three word classes','Ism / Fi\'l / Harf; POS tags are a practice aid, not a new learner taxonomy.'),
      ('Ch.2','I\'rab; status and signs; pronouns; Jarr; Harf al-Nasb and its Ism; Idafah','Preserve the classical Ism case system and particle governance. Distinguish the Ism case system from Mudari\' mood.'),
      ('Ch.3','Gender, number, qism/type','Use ILMHUB\'s current DiGNI labels for the learner-facing four properties. Do not silently treat the Bayyinah heading “type/qism” as a synonym for definiteness without a qualified crosswalk.'),
      ('Ch.4','Mawsuf/Sifah; Ism al-Isharah; Huruf al-\'Atf','Direct mapping to Tawsifi, Ishari and Atfi phrase work.'),
      ('Ch.5-6','Nominal sentence; Madi; Fa\'il; Maf\'ul; questions; complex structures','Direct mapping to Mubtada/Khabar and Fi\'l/Fa\'il/Maf\'ul, including phrases filling sentence slots.'),
      ('Ch.7-8','Mudari\'; governing particles; command/prohibition; passive','Keep Mudari\' mood distinct from noun case. Passive and Na\'ib al-Fa\'il are later sentence modules.'),
      ('Ch.9-11','Negation; Kana and sisters; compound Ism / An and its sisters','Store these as sentence and particle concepts rather than adding them to the six phrase types.'),
      ('Bayyinah Sarf Section','Forms, irregular/weak verbs, derived forms, plural patterns','Keep morphology and phrase syntax as related but separate data layers.'),
      ('Arabic101 85% guide','Function words/particles; thematic nouns; verb measures','Use frequency-first sequencing and spaced review only; do not reproduce copyrighted lists.'),
    ]
    add_table(doc,['Reference section','Topics','How it appears here'],book_rows,[1.35,2.1,2.95],7)

    doc.add_heading('3. Dataset architecture: three separate chunk layers',1)
    doc.add_paragraph('The term “chunk” is deliberately broad in the data model, but every row carries a layer, family, construction type, source type and evidence status. This prevents a repeated string, an annotated phrase span and a dependency relation from being treated as the same object.')
    layer_rows=[
      ('A. Grammar and constituent chunks','95,749','QAC Treebank constituent spans plus selected dependency-derived units (phrase constructions, sentence roles, particles and clause links).'),
      ('B. Chunk members and dependencies','207,074 member rows; 88,170 dependency edges','Written-word members are linked to segment-level POS, morphology, case, gloss and relation information.'),
      ('C. Repeated lexical chunks','25,188 normalized phrase types; 23,555 exact-diacritic phrase types; 150,935 location rows across both modes','Repeated contiguous 2+ word strings, occurring at least twice; suitable for lexical chunking and retrieval, not grammatical classification.'),
      ('D. Structure/navigation','62,901 strict containment links; 237,006 curriculum links','Supports nested chunk navigation and reuse of a single example across relevant lessons.'),
    ]
    add_table(doc,['Layer','Current size','What it means'],layer_rows,[1.4,1.55,3.45],8)

    doc.add_heading('4. The six ILMHUB phrase constructions: corpus evidence',1)
    doc.add_paragraph('Counts below are occurrences found in this QAC-derived annotation snapshot after conservative mapping rules. They are not a complete census of every possible classical Arabic construction in the Quran. “Badali” remains a candidate set pending teacher review.')
    rows=[]
    for r in six:
        rows.append((r['ilmhub_construction'],r['observed_count'],r['unique_ayah_count'],r['unique_surah_count'],r['interpretation_and_qualification']))
    add_table(doc,['Core construction','Occurrences','Ayah incidence','Surahs','Counting rule / qualification'],rows,[1.25,.7,.75,.55,3.2],7)
    note(doc,'Why the counts differ from source PP counts: a QAC PP constituent is a source-defined span, while a Jarri record is a preposition-to-governed-Ism dependency. They are related evidence units, not the same counting unit. A preposition attached as a prefix may share one written-word position with its governed Ism; the member table retains the segment distinction.')

    doc.add_heading('4.1 Source-defined QAC constituent spans',2)
    c_rows=[]
    for r in source_const:
        c_rows.append((r['construction_type'],r['occurrence_count'],r['unique_ayah_count'],r['unique_surah_count']))
    add_table(doc,['Source tag / span','Occurrences','Ayahs','Surahs'],c_rows,[2.6,1.1,1.1,1.1],8)
    doc.add_paragraph('PP is a prepositional phrase span; NS and VS are nominal and verbal sentence spans; SC is a subordinate-clause span; CS is a conditional-sentence span; S is a sentence span. NS/VS/CS/SC/S are not counted as extra ILMHUB phrase types.')

    doc.add_heading('5. Additional curriculum chunks beyond the six phrases',1)
    doc.add_paragraph('The following are useful for later modules in the supplied Bayyinah sequence. They are tagged as sentence slots, clause links or particle relations; they are not re-labelled as phrase constructions.')
    add_table(doc,['Additional concept','Observed relations','Ayahs','Surahs'],role_rows,[2.4,1.1,1.1,1.1],8)
    bullet(doc,'Subject and object work can display the entire noun phrase around the Fa\'il or Maf\'ul, then expose the internal Idafah/Tawsifi/Atfi structure.')
    bullet(doc,'Inna/Kana relations, negation, relative clauses and conditions provide staged transitions from the six foundational phrase patterns to sentence comprehension.')
    bullet(doc,'The source constituent file retains sentence/clause spans and the dependency table retains the links between words, phrases and clauses; do not flatten these into one POS sequence.')

    doc.add_heading('6. Data interpretation rules',1)
    rule_rows=[
      ('Repeated lexical chunk','A contiguous two-or-more-word string repeated at least twice within an ayah. It is a memorisable sequence, not automatically a phrase in the nahw sense.'),
      ('Source constituent','A phrase/clause/sentence span explicitly marked in the QAC-derived Treebank. Retain its original tag.'),
      ('Relation-derived construction','A learner-facing pattern inferred from a particular dependency edge, e.g. Poss → Idafi, Adj → Tawsifi, P-governed gen → Jarri. It remains “relation evidence”, not human reannotation.'),
      ('Badali','Only candidates from nominal App relations are listed. Apposition is broader than the exact ILMHUB Badali teaching pattern; do not publish as confirmed without review.'),
      ('Ishari','Counted as core only when a DEM head relates to a definite N/PN target. Indefinite-target examples are retained as review candidates because ILMHUB distinguishes a phrase from a complete statement.'),
      ('Atfi','The six-pattern Atfi subset requires nominal coordination and an explicit CONJ node. Verbal/clause coordination is stored separately.'),
      ('Morpheme vs written word','Prefix, stem and suffix segments may occupy one written word (e.g. preposition + noun or attached pronoun). Keep one display word and the segment-level member rows.'),
      ('Case and mood','Ism case is Raf\'/Nasb/Jarr. Mudari\' mood is Raf\'/Nasb/Jazm. Madi and Amr are Mabni; Jarr is never a verb mood/case.'),
      ('Cross-ayah boundaries','Grammar source spans can cross ayah boundaries and are explicitly flagged. Repeated lexical n-grams were defined within one ayah and never cross verse boundaries.'),
    ]
    add_table(doc,['Unit / rule','Interpretation'],rule_rows,[1.55,4.9],8)

    doc.add_heading('7. How the dataset should power the course',1)
    lesson_rows=[
      ('Word-class recognition','Use quran_chunk_members.csv and morphology fields to reveal Ism/Fi\'l/Harf at segment level.'),
      ('Ism DiGNI','Retrieve chunks containing Ism members and show definiteness, gender, number, case/state plus agreement in a descriptive phrase.'),
      ('Six phrase lessons','Filter quran_chunk_occurrences.csv by the six family labels; show member roles and full ayah context.'),
      ('Nominal/verbal sentence','Use NS/VS constituent spans and the subject/predicate/verb/agent/object relation chunks.'),
      ('Jarr / Idafah / Shibh al-Jumlah','Combine gen and Poss edges using shared member word IDs; use hierarchy links to expose nested spans.'),
      ('Kana / Inna / Negation','Filter the corresponding concept families and contrast the case roles without inventing sentence meanings.'),
      ('Vocabulary and memory','Use repeated_lexical_chunk_types.csv and repeated_lexical_chunk_occurrences.csv for frequency-based recognition and review.'),
      ('Ayah comprehension','Move from each chunk to its parent sentence span, then to the complete ayah, with word-by-word gloss and morphological notes.'),
    ]
    add_table(doc,['Curriculum area','Suggested use'],lesson_rows,[1.8,4.65],8)

    doc.add_heading('8. Limitations and quality controls',1)
    bullet(doc,'The source contains 77,432 whole-word positions and 11,693 Treebank sentence records. Syntax is a dependency analysis with segment-level annotations; it is not a teacher-authored lesson taxonomy.')
    bullet(doc,'The QAC documentation describes dependency edges between syntactic units and also notes that a written word may contain several morphological segments. This is why word and segment tables are separated.')
    bullet(doc,'Not all six phrase types are explicitly annotated as named categories in the Treebank. Tawsifi, Idafi, Jarri, Atfi and Ishari are derived conservatively from relation evidence; Badali is only a review queue.')
    bullet(doc,'Treebank syntactic assignments can embody interpretive decisions. Keep source IDs, source relations, uncertainty, and teacher review status so an Arabic grammar reviewer can accept, amend or reject each mapping.')
    bullet(doc,'No tafsir, theological interpretation or contextual meaning has been inferred. Glosses are corpus glosses, not translations of the full phrase in context.')
    bullet(doc,'The previous MASAQ Phrase_Function family is a separate taxonomy. Do not merge it with the six ILMHUB internal construction patterns; phrase-function is the external role of the chunk, while the six patterns describe internal construction.')

    doc.add_heading('9. Files in the CSV dataset',1)
    files_rows=[
      ('quran_chunk_occurrences.csv','Each explicit source constituent or selected dependency-derived phrase / sentence-role / clause chunk.'),
      ('quran_chunk_members.csv','Member words and source segments, roles, segment morphology, gloss, lemma/root and nominal/verb features.'),
      ('quran_dependency_edges.csv','All overt non-root dependency edges used to reconstruct and audit the grammar layer.'),
      ('quran_chunk_curriculum_links.csv','Many-to-many links from chunk IDs to curriculum concept IDs.'),
      ('quran_chunk_hierarchy.csv','Strict span-containment links for nested chunk navigation; containment does not itself prove grammatical dependency.'),
      ('quran_chunk_type_frequency.csv','Family, construction and source-tag totals.'),
      ('grammatical_chunk_pattern_frequency.csv','Repeated exact member-text patterns by structural family.'),
      ('six_core_phrase_pattern_summary.csv','A six-row snapshot aligned to the ILMHUB phrase taxonomy.'),
      ('repeated_lexical_chunk_types.csv','Repeated normalized and exact-diacritic lexical phrase types.'),
      ('repeated_lexical_chunk_occurrences.csv','Each occurrence of those repeated lexical phrases.'),
      ('curriculum_concept_map.csv','Curriculum IDs, lesson concepts, intended use and reference alignment.'),
      ('source_alignment_audit.csv','Explicit audit against the supplied books and ILMHUB.'),
      ('teacher_review_queue.csv','Badali and ambiguous construction candidates not cleared for instruction.'),
      ('dataset_summary.csv / data_dictionary.csv / source_manifest.csv','Population totals, table definitions and source SHA-256 hashes.'),
    ]
    add_table(doc,['CSV','Contents'],files_rows,[2.7,3.75],7)

    doc.add_heading('10. Sources and intellectual-property notes',1)
    refs=[
      'User-supplied: The Qur\'an\'s Language: A New Approach (Bayyinah Dream Arabic Program), Section 1: Nahw, Chapters 1-11; Section 2: Sarf, Chapters 1-13. Used as a curriculum crosswalk only; book pages are not reproduced in this pack.',
      'User-supplied: Islam Fekry, How to understand the Qur\'an in Arabic (Arabic101, 2025). The supplied FREE VERSION is labelled personal use only / not for sale or distribution. The dataset uses only the high-level frequency-sequencing idea and does not reproduce its lists or pages.',
      'ILMHUB, Foundations: https://www.ilmhub.org/arabic-grammar/foundations/',
      'ILMHUB, The Four Properties of ISM: https://www.ilmhub.org/courses/language-of-quran/book-1/l01-p1-four-properties-of-ism/',
      'ILMHUB, Phrases: https://www.ilmhub.org/arabic-grammar/phrases/',
      'ILMHUB, Essential Parts (Book 2): https://www.ilmhub.org/courses/language-of-quran/book-2/bk2-l01-p2/',
      'Quranic Arabic Corpus, Documentation: https://corpus.quran.com/documentation/',
      'Quranic Arabic Corpus, Morphological Features: https://corpus.quran.com/documentation/morphologicalfeatures.jsp',
      'Quranic Arabic Corpus, Syntactic Relations: https://corpus.quran.com/documentation/syntaxrelation.jsp',
    ]
    for x in refs: bullet(doc,x)
    note(doc,'Licensing review is required before redistribution or commercial deployment of any source-derived text, glosses or annotation assets. The supplied 85% book itself is not included in this dataset pack.')

    doc.add_paragraph('End of report. The CSV files are the working dataset; this report documents the selection and interpretation rules applied to those files.')
    doc.save(args.output)
    print(args.output)

if __name__=='__main__': main()
