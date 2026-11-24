# Source data, provenance and reuse notes

This project intentionally bundles only the source files used by the generators or needed to interpret their outputs. It does **not** bundle the supplied Bayyinah book PDF, the Arabic101 85% book PDF, recitation audio/JSONs, or unrelated files from the original archive.

## Bundled source files

| Source file | Pipeline use | Provenance / version note |
|---|---|---|
| `grammar/quranic-corpus-morphology-0.4.txt` | QAC POS, verb feature counts, Ism token membership | Quranic Arabic Corpus morphology v0.4. The file itself carries the Kais Dukes 2011 copyright and GNU GPL notice, plus Tanzil text attribution/terms. The copyright and licence blocks are retained verbatim. |
| `grammar/Quranic.csv` | QAC extended dependency/constituent counts and structured gender/number/case/state feature crosswalk | Supplied UTF-16 tab-separated convenience export. Do not assume it is identical to the raw v0.4 text file; POS assignments differ on some locations. |
| `grammar/MASAQ.csv` | MASAQ syntactic role and Ism family/morphology calculations | Supplied archive CSV. It has 157,676 data rows. That population does not reconcile with the published MASAQ paper's reported 131,930 morphology entries, so the script labels it as the *supplied MASAQ CSV*, not a verified V6 snapshot. The Mendeley Data V6 record lists CC BY-NC 3.0; verify that this exact file is that version and confirm rights before redistribution or commercial use. |
| `quran-script/wbw/uthmani-wbw.json` | QUL Uthmani surface-form frequency | Supplied QUL word-by-word source. Reuse terms may differ by individual QUL resource; verify current terms with QUL before redistribution or commercial deployment. Tanzil-related text attribution and restrictions may apply to source text embedded in derived resources. |
| `grammar/word-lemma.db` | QUL lemma mapping | Supplied QUL SQLite mapping database; resource-specific reuse terms should be checked. |
| `grammar/word-stem.db` | QUL stem mapping | Supplied QUL SQLite mapping database; resource-specific reuse terms should be checked. |
| `grammar/word-root.db` | QUL root mapping | Supplied QUL SQLite mapping database; resource-specific reuse terms should be checked. |
| `grammar/RelLabels.csv`, `grammar/ConstituentsTags.csv`, `grammar/CAPoS.csv` | Codebook/labels for QAC convenience export and POS reporting | Included with the supplied annotation archive. |
| `grammar/CAMorphFeatures.xlsx`, `grammar/CALemmaLexicon.csv`, `grammar/CARootLexicon.csv` | Supplementary codebooks / lexical reference for audit and interpretation | Included as companion reference files; current automated counts do not depend on every one of these files. |

## Public references

- Quranic Arabic Corpus morphology documentation: <https://corpus.quran.com/documentation/morphologicalfeatures.jsp>
- Quranic Arabic Corpus downloads: <https://corpus.quran.com/download>
- QUL resources: <https://qul.tarteel.ai/resources>
- MASAQ V6 Mendeley Data record: <https://data.mendeley.com/datasets/9yvrzxktmr/6>
- MASAQ research article: <https://pmc.ncbi.nlm.nih.gov/articles/PMC11741905/>
- Tanzil: <https://tanzil.net/download/>

## Important reuse restrictions

1. The QAC morphology file's GPL and attribution notice must be preserved. Its source file also asks for Quranic Arabic Corpus attribution and a link to `https://corpus.quran.com` when used in an application.
2. The Tanzil-derived text notice is included in the supplied QAC morphology file. The notice specifies CC BY-ND 3.0 for the relevant text; do not modify the source text or remove its attribution.
3. The MASAQ V6 Mendeley record lists CC BY-NC 3.0. That licence is non-commercial. The archive's CSV profile does not reconcile with the paper's published profile; verify the exact source version and permissions before embedding it in a commercial product.
4. QUL resources have individual provenance and licensing. Confirm current terms for each resource before redistribution or commercial use. This bundle preserves the supplied source files for reproducibility of the user's analysis; inclusion here is not a legal opinion that every item is cleared for public redistribution.
5. The two supplied book PDFs marked personal-use-only are excluded from this project. The analysis does not reproduce their text.

## Reproducibility note

`data_sources.zip` contains the original selected source files unchanged. `SOURCE_FILE_MANIFEST.csv` contains their SHA-256 hashes and byte sizes so a future run can verify that the same source bytes were used. Generated results are kept distinct from raw data in `output/csv/` and `output/reports/`.
