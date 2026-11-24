QUANTITATIVE ISM FEATURE DISTRIBUTIONS - METHODS AND LIMITATIONS

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
