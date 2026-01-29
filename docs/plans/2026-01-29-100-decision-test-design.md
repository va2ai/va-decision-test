# 100-Decision Test Design

## Goal

Validate the graph-lite schema by answering: "Given a claim issue, can I instantly show similar cases + the evidence/citation chains that mattered?"

## Tech Stack

- **Python** + **PostgreSQL** with pgvector
- **Docker** for Postgres
- **Gemini Flash** for LLM extraction
- **Embedded fetcher** (based on existing BVA scraper code)

## Project Structure

```
C:\code\va-decision-test\
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── src/
│   ├── db/
│   │   ├── schema.sql
│   │   └── connection.py
│   ├── fetcher/
│   │   ├── search.py           # BVA search logic
│   │   ├── parser.py           # Decision text parsing
│   │   └── selector.py         # Auto-select 100 by criteria
│   ├── extraction/
│   │   ├── gemini.py           # Gemini Flash client
│   │   ├── entities.py         # Extract entities
│   │   └── passages.py         # Chunk & tag passages
│   ├── graph/
│   │   ├── loader.py           # Insert nodes + edges
│   │   └── models.py           # Pydantic models
│   └── queries/
│       ├── q1_similar.py
│       ├── q2_evidence_chain.py
│       ├── q3_denial_why.py
│       ├── q4_evidence_diff.py
│       └── q5_authority_stats.py
├── scripts/
│   ├── setup.py
│   ├── ingest.py
│   └── validate.py
└── data/
    └── decisions/
```

## Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Core tables
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    decision_id TEXT UNIQUE NOT NULL,
    decision_date DATE,
    system_type TEXT,
    raw_text TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    decision_id INT REFERENCES decisions(id),
    issue_text TEXT NOT NULL,
    outcome TEXT,
    connection_type TEXT
);

CREATE TABLE conditions (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE authorities (
    id SERIAL PRIMARY KEY,
    citation TEXT UNIQUE NOT NULL
);

CREATE TABLE evidence_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE provider_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE passages (
    id SERIAL PRIMARY KEY,
    decision_id INT REFERENCES decisions(id),
    text TEXT NOT NULL,
    tag TEXT,
    embedding vector(768),
    confidence FLOAT DEFAULT 0.7
);

-- Edge tables
CREATE TABLE issue_conditions (
    issue_id INT REFERENCES issues(id),
    condition_id INT REFERENCES conditions(id),
    PRIMARY KEY (issue_id, condition_id)
);

CREATE TABLE issue_evidence (
    issue_id INT REFERENCES issues(id),
    evidence_type_id INT REFERENCES evidence_types(id),
    confidence FLOAT DEFAULT 0.7,
    PRIMARY KEY (issue_id, evidence_type_id)
);

CREATE TABLE issue_providers (
    issue_id INT REFERENCES issues(id),
    provider_type_id INT REFERENCES provider_types(id),
    PRIMARY KEY (issue_id, provider_type_id)
);

CREATE TABLE decision_authorities (
    decision_id INT REFERENCES decisions(id),
    authority_id INT REFERENCES authorities(id),
    PRIMARY KEY (decision_id, authority_id)
);

CREATE TABLE issue_passages (
    issue_id INT REFERENCES issues(id),
    passage_id INT REFERENCES passages(id),
    PRIMARY KEY (issue_id, passage_id)
);

-- Indexes
CREATE INDEX idx_decisions_embedding ON decisions USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_passages_embedding ON passages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_issues_outcome ON issues(outcome);
CREATE INDEX idx_passages_tag ON passages(tag);
```

## Auto-Selection Criteria

| Outcome  | Count |
|----------|-------|
| Granted  | 25    |
| Denied   | 25    |
| Remanded | 25    |
| Mixed    | 25    |

**Conditions:** tinnitus, sleep apnea secondary, PTSD, radiculopathy, cancer

**Special requirements:**
- At least 10 with private nexus language
- At least 10 with exam inadequacy language

## Gemini Flash Extraction

Single prompt per decision extracts:
- Issues with outcome, connection_type, condition
- Evidence types per issue (STR, VA_EXAM, PRIVATE_OPINION, LAY_EVIDENCE)
- Provider types per issue (VA_EXAMINER, PRIVATE_IME, TREATING_PHYSICIAN)
- Authorities cited (38 CFR, case law)
- Passages tagged (MEDICAL_OPINION, EXAM_ADEQUACY, LAY_EVIDENCE, REASONS_BASES)

Confidence: 0.6-0.7 for inferred, 0.9-1.0 for explicit.

## 5 MVP Queries

1. **Similar winning cases** - Input paragraph → top 5 similar passages with issue/outcome/condition
2. **Evidence chain** - Issue → condition, evidence types, providers, authorities, quotes
3. **Why denied** - Denied issue → missing edges + exam adequacy passages
4. **Evidence diff** - Condition → evidence frequency by outcome (grants vs denials)
5. **Authority stats** - Condition → authority citation counts by outcome

## Success Criteria

**PASS if:**
- All 5 queries work without schema changes
- Results interpretable without reading full decision
- Similarity search surfaces relevant cases

**FAIL if:**
- Need ad-hoc joins
- Wish relationships stored differently
- Similarity feels random
- Can't explain why outcome happened
