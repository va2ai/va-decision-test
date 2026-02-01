# 🚀 FastAPI Quickstart Guide

You now have a **production-ready REST API** for BVA decision analysis!

## What You Got

```
va-decision-test/
├── api/
│   ├── main.py           # FastAPI app with 11 endpoints
│   ├── models.py         # Pydantic request/response models
│   ├── services.py       # Business logic layer
│   ├── test_client.py    # Test script
│   └── README.md         # Full API documentation
├── Dockerfile            # Container image
└── docker-compose.yml    # API + PostgreSQL stack
```

## Start the API (3 ways)

### Option 1: Local Development (Fastest)

```bash
# Install dependencies
pip install -e ".[api]"

# Start PostgreSQL only
docker compose up postgres -d

# Start API locally
python api/main.py
```

### Option 2: Docker Compose (Recommended)

```bash
# Start everything (API + PostgreSQL)
docker compose up -d

# View logs
docker compose logs -f api
```

### Option 3: Manual uvicorn

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Access the API

Once running, open your browser:

- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Test It Out

### 1. Run the test client

```bash
python api/test_client.py
```

Expected output:
```
======================================================================
TEST: Health Check
======================================================================
Status: 200
Response: {'status': 'healthy', 'service': 'va-decision-api'}

======================================================================
TEST: Search BVA Decisions
======================================================================
Status: 200

Found 3 results:
  - A24084938 (2024)
    URL: https://www.va.gov/vetapp24/Files12/A24084938.txt
  - A24086283 (2024)
    URL: https://www.va.gov/vetapp24/Files12/A24086283.txt
  - A24082214 (2024)
    URL: https://www.va.gov/vetapp24/Files12/A24082214.txt

...

ALL TESTS PASSED ✓
```

### 2. Use curl

```bash
# Search for decisions
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tinnitus granted",
    "year": 2024,
    "max_results": 5
  }'

# Get a specific decision
curl "http://localhost:8000/api/v1/decision/A24084938?year=2024"

# Find similar cases
curl -X POST http://localhost:8000/api/v1/query/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "tinnitus noise exposure",
    "limit": 5
  }'

# Get evidence chain
curl "http://localhost:8000/api/v1/query/evidence-chain/1"

# Compare evidence by outcome
curl "http://localhost:8000/api/v1/query/evidence-diff?condition=tinnitus"

# Get authority citation stats
curl "http://localhost:8000/api/v1/query/authority-stats?condition=tinnitus"
```

### 3. Use Python

```python
import httpx

# Search decisions
response = httpx.post("http://localhost:8000/api/v1/search", json={
    "query": "tinnitus granted",
    "year": 2024,
    "max_results": 10
})

results = response.json()["results"]
print(f"Found {len(results)} decisions")

# Find similar cases
response = httpx.post("http://localhost:8000/api/v1/query/similar", json={
    "query_text": "tinnitus noise exposure",
    "limit": 5,
    "outcome_filter": "Granted"
})

cases = response.json()["results"]
for case in cases:
    print(f"{case['decision_id']}: {case['outcome']}")
```

## 11 Available Endpoints

### Search & Fetch (3 endpoints)
1. `POST /api/v1/search` - Search BVA decisions
2. `GET /api/v1/decision/{case_number}` - Fetch specific decision
3. `POST /api/v1/parse` - Parse decision text

### Extraction (1 endpoint)
4. `POST /api/v1/extract` - LLM entity extraction

### Queries - MVP Validation (5 endpoints)
5. `POST /api/v1/query/similar` - Find similar cases
6. `GET /api/v1/query/evidence-chain/{issue_id}` - Get evidence chain
7. `GET /api/v1/query/denial-analysis/{issue_id}` - Analyze denial
8. `GET /api/v1/query/evidence-diff` - Compare evidence by outcome
9. `GET /api/v1/query/authority-stats` - Citation statistics

### Ingestion (1 endpoint)
10. `POST /api/v1/ingest` - Full pipeline (fetch + parse + extract + load)

### System (1 endpoint)
11. `GET /health` - Health check

## Real-World Use Cases

### Use Case 1: Legal Research Tool

```python
# Frontend calls API to find similar winning cases
response = httpx.post("http://localhost:8000/api/v1/query/similar", json={
    "query_text": "tinnitus caused by noise exposure during military service",
    "limit": 10,
    "outcome_filter": "Granted"
})

# Display results to user
cases = response.json()["results"]
for case in cases:
    print(f"Similar case: {case['decision_id']}")
    print(f"Outcome: {case['outcome']}")
    print(f"Similarity: {case['similarity']:.2f}")
    print(f"Key passage: {case['passage'][:200]}...")
```

### Use Case 2: Evidence Gap Analysis

```python
# Analyze what evidence appears in grants vs denials
response = httpx.get(
    "http://localhost:8000/api/v1/query/evidence-diff",
    params={"condition": "tinnitus"}
)

evidence = response.json()["results"]

# Group by outcome
grants = [e for e in evidence if e["outcome"] == "Granted"]
denials = [e for e in evidence if e["outcome"] == "Denied"]

print("Evidence in GRANTS:")
for e in grants:
    print(f"  {e['evidence_type']}: {e['count']} cases")

print("\nEvidence in DENIALS:")
for e in denials:
    print(f"  {e['evidence_type']}: {e['count']} cases")

# Identify gaps
grant_types = {e["evidence_type"] for e in grants}
denial_types = {e["evidence_type"] for e in denials}
missing_in_denials = grant_types - denial_types

print(f"\nMissing in denials: {missing_in_denials}")
```

### Use Case 3: Automated Ingestion

```python
# Batch ingest recent decisions
import httpx
from datetime import datetime

decisions_to_ingest = [
    ("A24084938", 2024),
    ("A24086283", 2024),
    ("A24082214", 2024),
]

for case_number, year in decisions_to_ingest:
    print(f"Ingesting {case_number}...")

    response = httpx.post(
        "http://localhost:8000/api/v1/ingest",
        json={"case_number": case_number, "year": year},
        timeout=30
    )

    result = response.json()
    if result["success"]:
        print(f"✓ {case_number}: {result['issues_extracted']} issues extracted")
    else:
        print(f"✗ {case_number}: {result['message']}")
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│  (Web UI, Python scripts, curl, Postman, etc.)             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Search &   │  │  Extraction  │  │   Queries    │      │
│  │    Fetch     │  │   (LLM)      │  │  (5 MVP)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                          │                                   │
│  ┌──────────────────────▼────────────────────────────┐      │
│  │              Services Layer                        │      │
│  │  (Business logic, validation, error handling)     │      │
│  └──────────────────────┬────────────────────────────┘      │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Modules (src/)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ fetcher/ │  │extraction│  │  graph/  │  │ queries/ │   │
│  │ search & │  │  Gemini  │  │ Database │  │   SQL    │   │
│  │  parse   │  │   Flash  │  │  Loader  │  │  Queries │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL 16 + pgvector                        │
│  - Decisions, Issues, Conditions, Authorities, Passages     │
│  - Graph-lite schema with edges                             │
│  - 768-dim vector embeddings for similarity search          │
└─────────────────────────────────────────────────────────────┘
```

## Production Considerations

**Already included:**
- ✅ Pydantic validation
- ✅ Error handling
- ✅ CORS middleware
- ✅ OpenAPI documentation
- ✅ Health checks
- ✅ Docker deployment

**Add for production:**
- Rate limiting (slowapi)
- Authentication (API keys, OAuth)
- Caching (Redis)
- Background jobs (Celery, RQ)
- Monitoring (Prometheus, Sentry)
- Load balancing (nginx, Traefik)

## Next Steps

1. **Test the API**: `python api/test_client.py`
2. **Read full docs**: `api/README.md`
3. **Build a frontend**: Connect to the API from your web app
4. **Scale the corpus**: Use the API to ingest 100+ decisions
5. **Add features**: Custom queries, batch operations, webhooks

## Stop Services

```bash
# Docker Compose
docker compose down

# Or stop just the API
docker compose stop api
```

---

**🎉 You now have a reusable, production-ready API for BVA decision analysis!**
