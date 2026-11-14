# QLAC dual application prototypes

This package contains two independent, responsive, self-contained HTML prototypes. Open either file in a modern browser; no server, package installation, or internet connection is required.

## 1. `linguistic_explorer.html`
A research workspace prototype demonstrating:
- Search and filter over phrase/clause records
- Structural inspector with nested constituent relationships
- Query builder for level, structure, function, speech act, Quranic scope and review status
- Corpus analytics dashboard and research metrics
- Read-only source registry for EQTB/QAC and a distinct QLAC annotation layer
- Export of the demonstration result list as CSV

## 2. `quran_reader.html`
A reading-first prototype demonstrating:
- Quran reader presentation for selected Al-Mulk passages
- Plain, word, phrase, clause and all-layer reading modes
- Clickable word-level inspector
- Phrase and clause highlighting
- Structural hierarchy and source provenance panels
- Bookmark and navigation controls (prototype interactions)

## Important data and research caveats
- These are interface prototypes, not a connected production application or a live Quran corpus search engine.
- The sample content uses the Al-Mulk EQTB examples discussed in the project.
- EQTB source labels and spans such as VS [15–29], SC [22–29], NS [26–29], PP [2–3], and CS [3–18] are shown as source references.
- Any additional split of a larger construction into smaller clauses (for example, condition versus result in 67:10), any phrase taxonomy beyond the source labels, and all rhetorical classifications are explicitly draft illustrations requiring review by qualified Arabic grammar/tafsir reviewers.
- The examples do not claim that a complete, reviewed phrase/clause annotation set already exists.
- EQTB and QAC are treated as read-only reference sources. The intended QLAC dataset stores new annotation records, source identifiers, spans, relationships, evidence, review state and versioning—not duplicate token/morphology/codebook records.
- No translation or tafsir provider is connected in these prototypes.

## Suggested review sequence
1. Review the research explorer's data model and query dimensions.
2. Review the reader's highlight and annotation-inspector workflow.
3. Agree on phrase taxonomy and clause taxonomy.
4. Replace illustrative data with stable source references from the local EQTB/QAC adapters.
5. Add reviewed annotation records and connect actual search/analytics endpoints.
