-- Proposed schema for OUR NEW annotation layer only.
-- Do not import or copy EQTB/QAC source token/morphology tables into this schema.
-- Source records are resolved through versioned adapters.

CREATE TABLE source_datasets (
    source_dataset_id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    version TEXT NOT NULL,
    source_url TEXT,
    license_identifier TEXT,
    license_notes TEXT,
    checksum TEXT,
    UNIQUE (source_key, version)
);

-- One record per phrase/clause annotation that we create or need to annotate.
-- If an exact source entity already represents the unit, use unit_source_refs to
-- point to it; do not copy its text/attributes into this database.
CREATE TABLE annotation_units (
    unit_id TEXT PRIMARY KEY,
    unit_level TEXT NOT NULL CHECK (unit_level IN ('phrase', 'clause')),
    annotation_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (annotation_status IN ('candidate','pending','reviewed','accepted','uncertain','rejected')),
    taxonomy_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    general_note TEXT
);

-- A link to an existing source entity. source_record_key is interpreted by the
-- adapter for the specified source and version (for EQTB, e.g. tid or a
-- sentence_id/token_id constituent key).
CREATE TABLE unit_source_refs (
    unit_source_ref_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL REFERENCES annotation_units(unit_id),
    source_dataset_id TEXT NOT NULL REFERENCES source_datasets(source_dataset_id),
    source_entity_type TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    reference_role TEXT NOT NULL DEFAULT 'exact_entity'
        CHECK (reference_role IN ('exact_entity','evidence','candidate','derived_from','cross_check')),
    UNIQUE (unit_id, source_dataset_id, source_entity_type, source_record_key, reference_role)
);

-- Use only where we need to define a new span or a sub-span not represented by
-- an exact source entity. Endpoints reference source tokens; no token text copied.
-- Multiple ordered segments allow discontinuous constructions.
CREATE TABLE unit_span_segments (
    unit_id TEXT NOT NULL REFERENCES annotation_units(unit_id),
    segment_order INTEGER NOT NULL,
    source_dataset_id TEXT NOT NULL REFERENCES source_datasets(source_dataset_id),
    start_token_locator TEXT NOT NULL,
    end_token_locator TEXT NOT NULL,
    span_note TEXT,
    PRIMARY KEY (unit_id, segment_order)
);

-- Typed relationships between units. Direction is defined by relation_type.
CREATE TABLE unit_relationships (
    source_unit_id TEXT NOT NULL REFERENCES annotation_units(unit_id),
    target_unit_id TEXT NOT NULL REFERENCES annotation_units(unit_id),
    relation_type TEXT NOT NULL,
    evidence_source_ref_id TEXT REFERENCES unit_source_refs(unit_source_ref_id),
    annotator_note TEXT,
    PRIMARY KEY (source_unit_id, target_unit_id, relation_type),
    CHECK (source_unit_id <> target_unit_id)
);

-- Only classifications contributed by our project. A classification can be
-- attached to a source-backed unit or a newly defined unit.
CREATE TABLE unit_classifications (
    classification_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL REFERENCES annotation_units(unit_id),
    dimension TEXT NOT NULL CHECK (dimension IN (
        'phrase_structure',
        'clause_structure',
        'grammatical_function',
        'speech_act',
        'rhetorical_function',
        'discourse_function'
    )),
    category_id TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('candidate','pending','reviewed','accepted','uncertain','rejected')),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    annotator TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Evidence records point to source records; they do not duplicate those records.
CREATE TABLE annotation_evidence (
    evidence_id TEXT PRIMARY KEY,
    classification_id TEXT REFERENCES unit_classifications(classification_id),
    unit_id TEXT REFERENCES annotation_units(unit_id),
    source_dataset_id TEXT NOT NULL REFERENCES source_datasets(source_dataset_id),
    source_entity_type TEXT NOT NULL,
    source_record_key TEXT NOT NULL,
    evidence_role TEXT NOT NULL,
    explanation TEXT,
    CHECK (classification_id IS NOT NULL OR unit_id IS NOT NULL)
);

CREATE TABLE annotation_reviews (
    review_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL REFERENCES annotation_units(unit_id),
    classification_id TEXT REFERENCES unit_classifications(classification_id),
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accept','reject','revise','uncertain')),
    review_note TEXT,
    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_units_level_status ON annotation_units(unit_level, annotation_status);
CREATE INDEX idx_classifications_unit ON unit_classifications(unit_id, dimension);
CREATE INDEX idx_source_refs_source ON unit_source_refs(source_dataset_id, source_entity_type, source_record_key);
CREATE INDEX idx_relationships_target ON unit_relationships(target_unit_id, relation_type);
