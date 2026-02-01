# VA Decision Analysis System

**LLM Evaluation & Graph-Based Retrieval for Legal Decision Analysis**

A production-minded data pipeline and validation framework for extracting, structuring, and querying outcomes from long-form legal decisions using LLMs, vector similarity search, and a graph-lite relational schema.

While implemented on Board of Veterans' Appeals (BVA) decisions, this system is designed to validate generalizable patterns for legal and compliance AI: outcome extraction, evidence attribution, and similarity-based case research under ambiguous reasoning.

## Overview

This project answers a core applied-AI question:

**"Given a claim issue, can an LLM surface similar cases and explain which evidence and citations actually mattered?"**

To validate this, the system:

1. Selects a controlled, outcome-balanced corpus of legal decisions
2. Uses an LLM to extract structured entities and reasoning signals
3. Loads results into a PostgreSQL + pgvector graph-lite schema
4. Evaluates whether critical legal research queries can be answered without reading the full decision text

The goal is not automation of adjudication, but **decision support, transparency, and evaluation rigor**.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   BVA Search    │────▶│  Gemini Flash    │────▶│   PostgreSQL    │
│   (usa.gov)     │     │  Entity Extract  │     │   + pgvector    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
   Curated Corpus          Structured JSON          Graph-Lite Schema
   (100 decisions)         - Issues                 - Nodes: Decisions,
   - Granted               - Conditions               Issues, Conditions,
   - Denied                - Evidence Types           Authorities, Passages
   - Remanded              - Authorities            - Edges: Relationships
   - Mixed                 - Key Passages           - Vectors: Embeddings
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Database | PostgreSQL 16 + pgvector |
| LLM | Google Gemini 2.0 Flash |
| HTTP / Scraping | httpx, BeautifulSoup |
| Data Validation | Pydantic |
| Database Access | psycopg 3 (raw SQL) |
| Infra | Docker Compose |
| Testing | Pytest |

## Key Features

### 1. Outcome-Balanced Decision Selection

- Automated selection of 100 decisions evenly distributed across outcomes
  (25 granted / 25 denied / 25 remanded / 25 mixed)
- Coverage across multiple medical conditions to prevent single-domain bias
- Detection of legally significant patterns (e.g., private nexus opinions, exam inadequacy language)

### 2. LLM-Powered Entity & Reasoning Extraction

Structured extraction of:

- **Claim issues and conditions**
- **Outcomes and outcome rationale**
- **Evidence types** (STR, VA_EXAM, PRIVATE_OPINION, LAY_EVIDENCE)
- **Provider roles** (VA_EXAMINER, PRIVATE_IME, TREATING_PHYSICIAN)
- **Legal authorities** (38 CFR, precedential case law)
- **Key passage extraction** with confidence scoring
- **Explicit tagging of reasoning patterns** used by adjudicators

### 3. Graph-Lite Relational Schema

A relational model optimized for graph-style traversal without graph DB complexity:

- **Nodes**: Decisions, Issues, Conditions, Authorities, Evidence Types, Passages
- **Edges**: Junction tables with confidence and provenance metadata
- **Vectors**: 768-dimensional embeddings enabling semantic similarity search

This design supports **explainability, traceability, and auditability**.

### 4. MVP Validation Queries

The schema is considered valid only if it supports the following queries without schema changes:

| Query | What It Proves |
|-------|----------------|
| Similar Cases | Vector similarity surfaces genuinely comparable decisions |
| Evidence Chain | Full evidence trail for any issue can be reconstructed |
| Denial Analysis | Missing or weak evidence patterns can be identified |
| Evidence Diff | Clear contrasts between grant vs denial evidence |
| Authority Stats | Citation frequency correlates meaningfully with outcomes |

## Project Structure

```
va-decision-test/
├── src/
│   ├── db/              # Schema and connection management
│   ├── extraction/      # Gemini Flash entity extraction
│   ├── fetcher/         # BVA search, parsing, selection
│   ├── graph/           # Database loader
│   └── queries/         # 5 MVP query implementations
├── scripts/
│   ├── ingest.py        # Full ingestion pipeline
│   └── validate.py      # Schema validation runner
├── tests/               # Pytest test suite
└── docker-compose.yml   # PostgreSQL + pgvector
```

## Quick Start

```bash
# Start PostgreSQL with pgvector
docker compose up -d

# Configure environment
cp .env.example .env
# Add GEMINI_API_KEY

# Install dependencies
pip install -e ".[dev]"

# Run ingestion (start small)
python scripts/ingest.py --limit 5

# Score extracted issues
python scripts/score_issues.py

# Validate schema integrity
python scripts/validate.py

# Run reasoning validation
python scripts/validate_reasoning.py
```

## Schema Validation Criteria

**PASS if:**

- All MVP queries execute without schema changes
- Results are intelligible without reading full decision text
- Similarity search returns legally relevant cases

**FAIL if:**

- Ad-hoc joins are required for basic questions
- Relationships are lossy or ambiguous
- Outcomes cannot be meaningfully explained

## Why This Matters

In legal and compliance workflows, **opaque AI outputs are worse than no AI at all**.

This system demonstrates how to:

- **Surface precedent-like examples** with evidence attribution
- **Enable gap analysis** before decisions are finalized
- **Preserve reasoning transparency** and auditability
- **Evaluate LLMs on decision quality**, not just fluency

## Domain Portability

Although implemented on VA decisions, the same architecture applies to:

- Court opinions (state or federal)
- Administrative law rulings
- Insurance coverage determinations
- Regulatory enforcement actions
- Internal compliance adjudications

Only the document source and outcome schema change.

## Development

```bash
pytest tests/ -v
pytest tests/test_fetcher.py -v
SKIP_DB_TESTS=true pytest tests/ -v
```

## LEGALBENCH-Inspired Evaluation

Inspired by the **LEGALBENCH** legal reasoning benchmark, this system includes:

- **Dual-Score Evaluation:**
  - **Correctness** (logical validity)
  - **Depth** (quality of reasoning)

- **Rule Recall Metadata:** Explicit tracking of applied legal rules

- **Rhetorical Pattern Tags:**
  (NEGATIVE_CREDIBILITY, NO_NEXUS_FOUND, etc.)

- **Regression Gates:** Automated reasoning validation

See `docs/LEGALBENCH_ENHANCEMENTS.md` for details.

## License

MIT

---

**Built with Python, PostgreSQL, pgvector, and Gemini Flash. Designed for applied AI, evaluation rigor, and explainable legal decision support.**
