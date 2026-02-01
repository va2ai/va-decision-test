# VA Decision Analysis API

Production-ready FastAPI service for BVA decision analysis.

## Features

- **Search**: Query BVA decisions via USA.gov
- **Parse**: Extract structured metadata from decisions
- **Extract**: LLM-powered entity extraction (Gemini 2.0 Flash)
- **Query**: Graph-based similarity and evidence analysis
- **Ingest**: Full pipeline from search to database

## Quick Start

### 1. Install Dependencies

```bash
pip install -e ".[api]"
```

### 2. Start Services

```bash
# Start PostgreSQL
docker compose up -d

# Start API
python api/main.py
```

Or use uvicorn directly:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Search & Fetch

**POST /api/v1/search** - Search BVA decisions
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tinnitus granted",
    "year": 2024,
    "max_results": 10
  }'
```

**GET /api/v1/decision/{case_number}** - Fetch specific decision
```bash
curl "http://localhost:8000/api/v1/decision/A24084938?year=2024"
```

**POST /api/v1/parse** - Parse decision text
```bash
curl -X POST http://localhost:8000/api/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "..."}'
```

### Extraction

**POST /api/v1/extract** - Extract entities with LLM
```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "..."}'
```

### Queries (MVP Validation)

**POST /api/v1/query/similar** - Find similar cases
```bash
curl -X POST http://localhost:8000/api/v1/query/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "tinnitus noise exposure",
    "limit": 5,
    "outcome_filter": "Granted"
  }'
```

**GET /api/v1/query/evidence-chain/{issue_id}** - Get evidence chain
```bash
curl "http://localhost:8000/api/v1/query/evidence-chain/1"
```

**GET /api/v1/query/denial-analysis/{issue_id}** - Analyze denial
```bash
curl "http://localhost:8000/api/v1/query/denial-analysis/8"
```

**GET /api/v1/query/evidence-diff?condition=tinnitus** - Compare evidence by outcome
```bash
curl "http://localhost:8000/api/v1/query/evidence-diff?condition=tinnitus"
```

**GET /api/v1/query/authority-stats?condition=tinnitus** - Authority citation stats
```bash
curl "http://localhost:8000/api/v1/query/authority-stats?condition=tinnitus"
```

### Ingestion

**POST /api/v1/ingest** - Full ingestion pipeline
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "A24084938",
    "year": 2024
  }'
```

## Response Examples

### Search Response
```json
{
  "results": [
    {
      "url": "https://www.va.gov/vetapp24/Files12/A24084938.txt",
      "case_number": "A24084938",
      "title": "A24084938.txt",
      "snippet": "...percent evaluation for bilateral tinnitus is granted...",
      "year": 2024
    }
  ],
  "count": 1
}
```

### Similar Cases Response
```json
{
  "results": [
    {
      "passage": "The veteran's private IME opined...",
      "issue_text": "Service connection for tinnitus",
      "outcome": "Granted",
      "condition": "tinnitus",
      "decision_id": "A25086438",
      "similarity": 0.89
    }
  ],
  "count": 5
}
```

### Evidence Chain Response
```json
{
  "issue_id": 1,
  "condition": "tinnitus",
  "outcome": "Granted",
  "evidence_types": ["VA_EXAM", "PRIVATE_OPINION", "LAY_EVIDENCE"],
  "provider_types": ["VA_EXAMINER", "PRIVATE_IME"],
  "authorities": ["38 C.F.R. § 3.303", "38 C.F.R. § 3.310"],
  "passages": ["The veteran's private IME opined..."]
}
```

## Use Cases

### 1. Legal Research
```python
import httpx

# Find similar winning cases for tinnitus
response = httpx.post("http://localhost:8000/api/v1/query/similar", json={
    "query_text": "tinnitus caused by noise exposure during service",
    "limit": 10,
    "outcome_filter": "Granted"
})

cases = response.json()["results"]
for case in cases:
    print(f"{case['decision_id']}: {case['outcome']} - {case['similarity']:.2f}")
```

### 2. Evidence Gap Analysis
```python
# Compare evidence in grants vs denials
response = httpx.get(
    "http://localhost:8000/api/v1/query/evidence-diff",
    params={"condition": "tinnitus"}
)

evidence = response.json()["results"]
grants = [e for e in evidence if e["outcome"] == "Granted"]
denials = [e for e in evidence if e["outcome"] == "Denied"]

print(f"Evidence in grants: {grants}")
print(f"Evidence in denials: {denials}")
```

### 3. Batch Ingestion
```python
# Ingest multiple decisions
decisions = ["A24084938", "A24086283", "A24082214"]

for case_number in decisions:
    response = httpx.post("http://localhost:8000/api/v1/ingest", json={
        "case_number": case_number,
        "year": 2024
    })
    print(response.json())
```

## Architecture

```
┌──────────────┐
│   FastAPI    │  ← REST API layer
└──────┬───────┘
       │
┌──────▼───────┐
│   Services   │  ← Business logic
└──────┬───────┘
       │
┌──────▼───────┐
│  src/        │  ← Core modules
│  - fetcher/  │     - Search & parse
│  - extraction/│    - LLM extraction
│  - graph/    │     - Database loader
│  - queries/  │     - SQL queries
└──────┬───────┘
       │
┌──────▼───────┐
│  PostgreSQL  │  ← pgvector database
│  + pgvector  │
└──────────────┘
```

## Production Deployment

### Docker Compose

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/va_decisions
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - postgres

  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=va_decisions
```

### Environment Variables

Create `.env` file:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/va_decisions
GEMINI_API_KEY=your_key_here
```

## Performance Notes

- **LLM extraction**: 5-10 seconds per decision (Gemini 2.0 Flash)
- **Vector similarity**: <100ms with pgvector
- **Search**: 2-5 seconds (rate limited by USA.gov)
- **Ingestion**: ~15 seconds per decision (full pipeline)

For production, consider:
- Background task queue (Celery, RQ)
- Redis caching for search results
- Rate limiting middleware
- API key authentication

## Testing

```bash
# Run API tests
pytest tests/test_api.py -v

# Test with real API
python api/test_client.py
```

## License

MIT
