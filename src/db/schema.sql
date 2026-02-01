CREATE EXTENSION IF NOT EXISTS vector;

-- Core tables
CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    decision_id TEXT UNIQUE NOT NULL,
    decision_date DATE,
    system_type TEXT,
    raw_text TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    decision_id INT REFERENCES decisions(id) ON DELETE CASCADE,
    issue_text TEXT NOT NULL,
    outcome TEXT,
    connection_type TEXT,
    correctness_score FLOAT DEFAULT NULL,
    analysis_depth_score FLOAT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS conditions (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS authorities (
    id SERIAL PRIMARY KEY,
    citation TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS passages (
    id SERIAL PRIMARY KEY,
    decision_id INT REFERENCES decisions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    tag TEXT,
    embedding vector(768),
    confidence FLOAT DEFAULT 0.7
);

-- Edge tables
CREATE TABLE IF NOT EXISTS issue_conditions (
    issue_id INT REFERENCES issues(id) ON DELETE CASCADE,
    condition_id INT REFERENCES conditions(id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, condition_id)
);

CREATE TABLE IF NOT EXISTS issue_evidence (
    issue_id INT REFERENCES issues(id) ON DELETE CASCADE,
    evidence_type_id INT REFERENCES evidence_types(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 0.7,
    PRIMARY KEY (issue_id, evidence_type_id)
);

CREATE TABLE IF NOT EXISTS issue_providers (
    issue_id INT REFERENCES issues(id) ON DELETE CASCADE,
    provider_type_id INT REFERENCES provider_types(id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, provider_type_id)
);

CREATE TABLE IF NOT EXISTS decision_authorities (
    decision_id INT REFERENCES decisions(id) ON DELETE CASCADE,
    authority_id INT REFERENCES authorities(id) ON DELETE CASCADE,
    PRIMARY KEY (decision_id, authority_id)
);

CREATE TABLE IF NOT EXISTS issue_passages (
    issue_id INT REFERENCES issues(id) ON DELETE CASCADE,
    passage_id INT REFERENCES passages(id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, passage_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_issues_outcome ON issues(outcome);
CREATE INDEX IF NOT EXISTS idx_passages_tag ON passages(tag);
