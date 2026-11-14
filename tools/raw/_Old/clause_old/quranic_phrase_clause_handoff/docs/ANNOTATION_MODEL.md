# Annotation Model: Phrase and Clause Levels

## 1. Existing word/morphology level

This level is supplied by EQTB/QAC. It is an input/reference layer, not a new dataset we are creating.

Examples: tokenization, text, root, lemma, POS, case, mood, aspect, gender, number, prefixes, suffixes, dependency relations.

## 2. Phrase level

A phrase is a syntactic unit formed by one or more words/tokens. Phrase boundaries and types must be defined according to a documented Arabic/linguistic annotation guideline.

Candidate phrase types for investigation (not yet a finalized taxonomy):

- noun phrase;
- prepositional phrase / شبه الجملة;
- adjective or adjectival phrase;
- adverbial/locative/temporal phrase;
- verb phrase, where the adopted grammatical framework recognizes it as a constituent;
- construct/annexation phrase (الإضافة), if represented as a phrase unit under the selected framework.

Important: EQTB already has PP constituents. Reuse exact PP records rather than creating duplicate PP phrase annotations. EQTB's NS/VS/CS/SC are not a complete phrase inventory; they are sentence/clause-like constituent labels in the source scheme.

For each genuinely new phrase annotation, store only:

- internal phrase/annotation ID;
- phrase type from our taxonomy;
- one or more token-span references (if not an exact existing source entity);
- optional head-token reference;
- relationships to parent/containing phrase or clause;
- source evidence references;
- annotator, version, review status, and confidence/rationale where relevant.

Do not copy Arabic text or word morphology. Resolve them from source tokens.

## 3. Clause level

A clause annotation identifies a clause span or references an existing source constituent that already represents the exact clause.

Potential clause constructions to evaluate include:

- nominal clause (الجملة الاسمية);
- verbal clause (الجملة الفعلية);
- conditional clause / condition (جملة الشرط);
- conditional result (جواب الشرط);
- relative clause (صلة الموصول);
- circumstantial clause (جملة الحال);
- causal clause (جملة التعليل);
- purpose clause (جملة الغاية);
- interrogative clause (جملة الاستفهام);
- imperative clause (جملة الأمر);
- prohibitive clause (جملة النهي);
- subordinate clause and other clause types defined by the selected grammar framework.

Do not assume these are mutually exclusive or all belong to one taxonomy dimension. Structural type and syntactic function must be separate.

## 4. Classification dimensions

### Structural type

What construction is this unit? Examples: nominal, verbal, conditional, relative, subordinate.

### Grammatical/syntactic function

What role does it play? Examples: condition, result, circumstantial, cause, purpose, subject clause, object/complement clause, relative clause function.

### Speech act / clause mode

What communicative form is expressed? Examples: declarative, imperative, prohibition, interrogative, vocative, wish. The exact taxonomy needs scholarly review.

### Rhetorical/discourse function

What discourse/rhetorical work does it do? Examples: emphasis, oath, warning, threat, promise, glad tidings. Some may apply to spans larger than one clause; support span-scoped annotations rather than forcing every feature onto a single clause.

## 5. Relationships

Use typed relationships rather than encoding relationships as labels on the same clause:

- `contains` / `contained_by` (can be derived from spans; avoid storing both if redundant);
- `condition_of` / `result_of`;
- `subordinate_to`;
- `relative_clause_of`;
- `coordinates_with`;
- `continues` or other discourse links only when defined by an annotation guideline.

For a conditional construction, the condition and result should be represented as separate clause units when the linguistic analysis supports separate boundaries, linked by a condition-result relationship. An EQTB CS span may cover the larger construction; it does not automatically supply both child clause spans.

## 6. Hierarchy and overlap

The project workflow is word/morphology → phrase → clause. This does not mean all real Arabic structures are a simple tree. Clauses may be embedded; spans may overlap; a word may participate in a larger construction; coordination and ellipsis may require special handling. The data model must support nesting, cross-links, and multiple span segments.

## 7. Annotation status

Recommended statuses:

- `candidate` — suggested automatically from source structure;
- `pending` — awaiting review;
- `reviewed` — checked by an annotator;
- `accepted` — approved as part of the released annotation set;
- `uncertain` — plausible but unresolved;
- `rejected` — reviewed and not accepted.

A candidate must never be exposed as a verified gold label without review.
