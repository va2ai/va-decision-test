# VA Decision Analysis System

A data pipeline and validation framework for analyzing Board of Veterans' Appeals (BVA) decisions using graph-based entity extraction and vector similarity search.

## Overview

This project validates a **graph-lite schema** for answering a critical question in veterans' claims analysis:

> "Given a claim issue, can I instantly show similar cases and the evidence/citation chains that mattered?"

The system selects 100 diverse BVA decisions, extracts structured entities using LLM-powered analysis, loads them into a PostgreSQL graph schema with pgvector embeddings, and validates the model through 5 MVP queries.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   BVA Search    │────▶│  Gemini Flash    │────▶│   PostgreSQL    │
│   (usa.gov)     │     │  Entity Extract  │     │   + pgvector    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
   100 Decisions          Structured JSON          Graph Schema
   - 25 Granted           - Issues                 - Nodes: Decisions,
   - 25 Denied            - Conditions               Issues, Conditions,
   - 25 Remanded          - Evidence Types           Authorities, Passages
   - 25 Mixed             - Authorities            - Edges: Relationships
                          - Key Passages           - Vectors: Embeddings
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Database | PostgreSQL 16 + pgvector |
| LLM | Google Gemini 2.0 Flash |
| HTTP | httpx + BeautifulSoup |
| ORM | psycopg 3 (raw SQL) |
| Validation | Pydantic |
| Infrastructure | Docker Compose |

## Key Features

### Intelligent Decision Selection
- Automated selection of 100 decisions across outcome types (granted/denied/remanded/mixed)
- Coverage across 5 medical conditions (tinnitus, PTSD, sleep apnea, radiculopathy, cancer)
- Detection of special patterns (private nexus opinions, exam inadequacy language)

### LLM-Powered Entity Extraction
- Structured extraction of issues, conditions, and outcomes
- Evidence type classification (STR, VA_EXAM, PRIVATE_OPINION, LAY_EVIDENCE)
- Provider type identification (VA_EXAMINER, PRIVATE_IME, TREATING_PHYSICIAN)
- Legal authority citation parsing (38 CFR, case law)
- Key passage extraction with confidence scoring

### Graph-Lite Schema
Relational schema optimized for graph-style queries:
- **Nodes**: Decisions, Issues, Conditions, Authorities, Evidence Types, Passages
- **Edges**: Junction tables capturing relationships with confidence scores
- **Vectors**: 768-dim embeddings for semantic similarity search

### 5 MVP Validation Queries

| Query | Purpose |
|-------|---------|
| Similar Cases | Vector similarity search for related decisions |
| Evidence Chain | Full evidence trail for any issue |
| Denial Analysis | Identify missing evidence in denied claims |
| Evidence Diff | Compare evidence patterns: grants vs denials |
| Authority Stats | Citation frequency by outcome |

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
# Edit .env with your GEMINI_API_KEY

# Install dependencies
pip install -e ".[dev]"

# Run ingestion (start with 5 decisions to test)
python scripts/ingest.py --limit 5

# Score issues with LEGALBENCH-inspired dual scores
python scripts/score_issues.py

# Validate the schema
python scripts/validate.py

# Run LEGALBENCH-style reasoning validation
python scripts/validate_reasoning.py
```

## Schema Validation Criteria

**PASS if:**
- All 5 queries execute without schema changes
- Results are interpretable without reading full decisions
- Similarity search surfaces genuinely relevant cases

**FAIL if:**
- Ad-hoc joins needed for basic queries
- Relationships stored incorrectly
- Can't explain why an outcome happened

## Why This Matters

Veterans navigating the VA claims process often lack visibility into what evidence patterns lead to successful outcomes. This system enables:

1. **Pattern Discovery**: What evidence appears in grants but not denials?
2. **Case Research**: Find similar winning cases instantly
3. **Gap Analysis**: Identify missing evidence before submission
4. **Authority Mapping**: Which legal citations correlate with success?

## Development

```bash
# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_fetcher.py -v

# Skip database-dependent tests
SKIP_DB_TESTS=true pytest tests/ -v
```

## LEGALBENCH-Inspired Enhancements

This system includes rigorous evaluation features inspired by the LEGALBENCH legal reasoning benchmark:

- **Dual-Score Evaluation**: Separates correctness (logical validity) from analysis depth (reasoning quality)
- **Rule-Recall Metadata**: Explicitly tracks legal rules identified in decisions
- **Rhetorical Understanding**: Tags for VA reasoning patterns (NEGATIVE_CREDIBILITY, NO_NEXUS_FOUND, etc.)
- **Validation Suite**: Automated pass/fail gates for regression prevention

See [docs/LEGALBENCH_ENHANCEMENTS.md](docs/LEGALBENCH_ENHANCEMENTS.md) for details.

## License

MIT

---

*Built with Python, PostgreSQL, and Gemini Flash*
