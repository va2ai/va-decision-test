# 📈 Scaling to 100 Decisions Guide

Complete guide to scaling your VA decision corpus to 100 balanced decisions using the FastAPI.

## Current Status

✅ **FastAPI operational** - All endpoints tested and working
✅ **Database ready** - PostgreSQL + pgvector configured
✅ **20 decisions** already ingested (from initial testing)
✅ **5/5 MVP queries** passing validation
⚠️ **Gemini API key** needs to be refreshed/regenerated

---

## What We Built

### 1. Balanced Selector (`src/fetcher/balanced_selector.py`)

Intelligent decision selector that ensures:
- **25 granted** / **25 denied** / **25 remanded** / **25 mixed**
- **10+** with private nexus opinions
- **10+** with exam inadequacy language
- Diverse conditions (tinnitus, sleep apnea, PTSD, radiculopathy, knee)

**Features:**
- Smart quota tracking
- Progress reporting every 10 decisions
- Prioritizes special requirements
- Searches broadly to find mixed outcomes

### 2. API Scaling Scripts

**`scripts/scale_to_100.py`** - Full ingestion pipeline:
```
Select 100 → Ingest via API → Validate corpus
```

**`scripts/test_scale.py`** - Quick test (3 decisions):
```
Test search → Test ingest → Report results
```

### 3. API Services Fixes

Fixed `api/services.py` to properly handle Pydantic models:
- `ExtractionResult` is a Pydantic model, not a dict
- Access `.issues` attribute instead of `.get("issues")`
- Correctly construct `PassageData` from `ExtractedPassage`

---

## Prerequisites

### 1. API Running ✓

```bash
# Check if running
curl http://localhost:8000/health

# If not running, start it
uvicorn api.main:app --reload
```

### 2. PostgreSQL Running ✓

```bash
docker compose up postgres -d
```

### 3. Gemini API Key ⚠️

**Issue:** Current API key has permission error (403 PERMISSION_DENIED)

**Solution:**
1. Go to https://aistudio.google.com/apikey
2. Create a new API key or regenerate existing one
3. Update `.env` file:
   ```
   GEMINI_API_KEY=your_new_key_here
   ```
4. Restart the API:
   ```bash
   # Stop current API (Ctrl+C)
   # Start again
   uvicorn api.main:app --reload
   ```

---

## Scaling Process

### Option 1: Full 100 Decisions (Recommended)

```bash
# Ensure API is running
curl http://localhost:8000/health

# Run scaling script
python scripts/scale_to_100.py
```

**Estimated time:** 20-30 minutes
- 10-15 min: Selection (rate-limited searches)
- 15-20 min: Ingestion (LLM extraction per decision)

**Progress:**
- Saves selection to `data/selection_100.json`
- Reports progress every 10 decisions
- Validates corpus at the end

### Option 2: Test First (Recommended)

```bash
# Test with 3 decisions first
python scripts/test_scale.py

# If all pass, run full scaling
python scripts/scale_to_100.py
```

---

## Expected Output

### Selection Phase
```
==================================================================
Searching condition: tinnitus
==================================================================
  Year 2025: tinnitus
    ✓ A25086438: granted (PN=True, EI=False)
    ✓ A25052378: granted (PN=True, EI=False)

Progress Report:
Total: 10/100

Outcomes:
  Granted: 5/25
  Denied: 3/25
  Remanded: 2/25
  Mixed: 0/25

Special Requirements:
  Private Nexus: 3/10
  Exam Inadequacy: 1/10
```

### Ingestion Phase
```
[1/100] Ingesting A25086438...
  ✓ Success: 1 issues extracted

[10/100] Progress: 10/100 (10.0%)
Elapsed: 2.5m | Estimated remaining: 22.5m
```

### Validation Phase
```
====================================================================
VALIDATING CORPUS
====================================================================

Total decisions: 100

Outcome distribution:
  Granted: 25
  Denied: 25
  Remanded: 25
  Mixed: 25

Top conditions:
  tinnitus: 35 issues
  sleep apnea secondary: 20 issues
  PTSD: 18 issues

Evidence types:
  VA_EXAM: 75
  LAY_EVIDENCE: 60
  PRIVATE_OPINION: 45
  STR: 30

Decisions with private nexus patterns: ~12
Decisions with exam inadequacy patterns: ~11

====================================================================
VALIDATION RESULTS
====================================================================
✓ PASS: Total decisions >= 100
✓ PASS: Granted decisions >= 20
✓ PASS: Denied decisions >= 20
✓ PASS: Remanded decisions >= 20
✓ PASS: Private nexus >= 10
✓ PASS: Exam inadequacy >= 10

🎉 ALL VALIDATION CHECKS PASSED!
```

---

## Troubleshooting

### Issue: "API is not running"
```bash
# Solution: Start the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Issue: "403 PERMISSION_DENIED" (Gemini API)
```bash
# Solution: Regenerate API key
# 1. Visit https://aistudio.google.com/apikey
# 2. Create new key
# 3. Update .env
# 4. Restart API
```

### Issue: "Connection refused" (PostgreSQL)
```bash
# Solution: Start PostgreSQL
docker compose up postgres -d
```

### Issue: Script fails partway through
```bash
# The selection is saved to data/selection_100.json
# You can manually resume by modifying the script
# Or just re-run - it will skip duplicates based on decision_id
```

### Issue: "Rate limited by USA.gov"
```bash
# The script has 1.5-2 second delays built in
# If you still hit rate limits, the script will log warnings
# and continue with other conditions
```

---

## Validation After Scaling

```bash
# Run MVP validation queries
python scripts/validate.py

# Expected output: 5/5 queries passed
```

### Check corpus stats:
```python
from src.db.connection import get_connection

conn = get_connection()

# Total decisions
cur = conn.execute("SELECT COUNT(*) FROM decisions")
print(f"Total: {cur.fetchone()[0]}")

# Outcome distribution
cur = conn.execute("""
    SELECT outcome, COUNT(*) FROM issues
    GROUP BY outcome ORDER BY outcome
""")
for row in cur:
    print(f"{row[0]}: {row[1]}")
```

---

## What You Get

After successful scaling:

### ✅ Balanced Corpus
- 100 decisions with 25/25/25/25 distribution
- Diverse conditions and years
- Special patterns captured

### ✅ Complete Graph Schema
- Decisions, Issues, Conditions
- Evidence types, Provider types
- Authorities, Key passages
- Vector embeddings for similarity

### ✅ Validated Queries
- Similar cases search
- Evidence chain reconstruction
- Denial analysis
- Evidence comparison
- Authority statistics

### ✅ Production API
- 11 REST endpoints operational
- Interactive documentation
- Language-agnostic access

---

## Alternative: Manual Ingestion (Without API)

If you prefer to bypass the API:

```python
from src.fetcher.balanced_selector import select_100_balanced
from src.extraction.gemini import extract_entities
from src.graph.loader import load_decision
from src.db.connection import get_connection, init_schema

# Select decisions
decisions = select_100_balanced()

# Ingest each one
conn = get_connection()
init_schema(conn)

for decision in decisions:
    extraction = extract_entities(decision["text"])
    load_decision(
        conn=conn,
        decision_id=decision["case_number"],
        raw_text=decision["text"],
        decision_date=decision["parsed"].get("decision_date"),
        extraction=extraction
    )
    conn.commit()
    print(f"✓ {decision['case_number']}")

conn.close()
```

---

## Next Steps After Scaling

1. **Run validation**: `python scripts/validate.py`
2. **Test API queries**: Open http://localhost:8000/docs
3. **Build a frontend**: Use the API endpoints
4. **Add more queries**: Extend the query library
5. **Deploy to production**: Use Docker Compose

---

## Performance Notes

**Selection:**
- ~5-10 decisions per minute (rate limited by USA.gov)
- 100 decisions = 10-20 minutes

**Ingestion:**
- ~3-4 decisions per minute (LLM extraction)
- 100 decisions = 25-30 minutes

**Total:** ~35-50 minutes for full corpus

**Optimization ideas:**
- Batch LLM requests (if Gemini supports it)
- Parallel ingestion (multiple API workers)
- Cache search results
- Pre-download decision texts

---

## Summary

**Status:** Ready to scale, pending Gemini API key refresh

**Commands:**
```bash
# 1. Regenerate Gemini API key
# 2. Update .env
# 3. Restart API: uvicorn api.main:app --reload
# 4. Test: python scripts/test_scale.py
# 5. Scale: python scripts/scale_to_100.py
```

**What happens:**
1. Selects 100 balanced decisions (10-15 min)
2. Ingests via API with LLM extraction (15-20 min)
3. Validates corpus meets all criteria
4. You have a production-ready legal decision analysis system!

🚀 **Ready to scale when you refresh the API key!**
