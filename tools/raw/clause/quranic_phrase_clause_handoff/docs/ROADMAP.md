# Roadmap

## Phase 0 — Freeze architecture and source contracts

- [x] Establish that EQTB and QAC remain immutable source datasets.
- [x] Decide that the new dataset stores annotations/references only.
- [x] Record actual EQTB token/constituent identifier behavior.
- [ ] Verify source release/version and license metadata for each input file.
- [ ] Define a versioned source registry and adapter contract.

**Exit criteria:** Every source entity we reference has an unambiguous dataset key, version and locator strategy.

## Phase 1 — Source adapters and reference resolver

- [ ] Implement read-only EQTB adapter.
- [ ] Implement read-only QAC morphology adapter.
- [ ] Implement EQTB constituent resolver using `sentence_id` + inclusive `constituents_loc` token ranges.
- [ ] Implement QAC coordinate resolver.
- [ ] Resolve implicit EQTB tokens without fabricating Quranic word locations.
- [ ] Test that source files are not modified.

**Exit criteria:** Given a source reference, the app/tool can retrieve the original row and resolve its text/features on demand.

## Phase 2 — Phrase annotation proof of concept (Surah 67)

- [ ] Inventory all existing EQTB PP and other potentially phrase-relevant constituents.
- [ ] Decide which phrase information is already adequately represented in EQTB.
- [ ] Draft a phrase taxonomy grounded in a chosen Arabic grammatical framework.
- [ ] Identify phrase spans missing from source coverage.
- [ ] Store only new phrase annotations and references.
- [ ] Validate a representative sample manually.

**Exit criteria:** A phrase annotation export contains no copied word text/morphology and every annotation has provenance and review status.

## Phase 3 — Clause annotation proof of concept (Surah 67)

- [ ] Inventory EQTB CS/SC/NS/VS and relevant dependency evidence.
- [ ] Distinguish whole conditional constructions from condition/result clause spans.
- [ ] Extract/annotate missing clause boundaries.
- [ ] Preserve nested and cross-verse sentence structures.
- [ ] Add typed clause relationships.
- [ ] Validate spans against Arabic grammar and appropriate scholarly references.

**Exit criteria:** Each accepted clause can be traced to exact source token references and has a reviewed structural analysis.

## Phase 4 — Clause classifications

- [ ] Finalize structural type taxonomy.
- [ ] Finalize grammatical-function taxonomy.
- [ ] Finalize speech-act taxonomy.
- [ ] Finalize rhetorical/discourse taxonomy.
- [ ] Define annotation guidelines and adjudication rules.
- [ ] Add evidence and reviewer workflow.

**Exit criteria:** Two annotators can apply the guideline consistently to a sample; disagreements are measured and documented.

## Phase 5 — Full Quran expansion

- [ ] Test on several structurally diverse surahs.
- [ ] Refine extraction and annotation guidelines.
- [ ] Scale to all 114 surahs.
- [ ] Version datasets and retain historical annotation decisions.

## Phase 6 — Application integration

- [ ] Build phrase/clause browsing and search.
- [ ] Resolve Arabic text/morphology from original sources.
- [ ] Filter by type, function, root, lemma, surah and verse.
- [ ] Display source citations and annotation provenance.
- [ ] Expose uncertain/pending status clearly.

## Immediate next action

Start Phase 1: implement read-only source adapters and a source-reference resolver. Do not extend the earlier pipeline by adding more copied/enriched CSV exports. Use the existing Surah 67 data to validate references, then create a small phrase-level annotation layer containing only genuinely new units and classifications.
