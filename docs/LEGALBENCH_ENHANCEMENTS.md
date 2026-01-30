# LEGALBENCH-Inspired Enhancements

This document describes the enhancements made to the VA Decision Analysis System inspired by the LEGALBENCH legal AI benchmark.

## Overview

LEGALBENCH is a rigorous legal reasoning benchmark that tests AI systems on:
- **Rule-Recall**: Can the model state the legal rule?
- **Rule-Application**: Can it apply facts to legal elements?
- **Interpretation**: Can it find similar precedents?
- **Rhetorical Understanding**: Can it recognize legal argumentation patterns?

We've adapted these principles to create a defensible, auditable VA decision analysis system.

## Enhancement 1: Dual-Score Evaluation

### What It Does
Separates **correctness** (logical validity) from **analysis depth** (reasoning quality).

### Schema Changes
```sql
ALTER TABLE issues ADD COLUMN correctness_score FLOAT DEFAULT NULL;
ALTER TABLE issues ADD COLUMN analysis_depth_score FLOAT DEFAULT NULL;
```

### Correctness Score (0.0-1.0)
Penalizes logical errors:
- ❌ Outcome contradicts ORDER section
- ❌ Evidence claimed but no passage tagged
- ❌ Authority cited but not in text
- ❌ Granted without evidence
- ❌ Denied despite overwhelming evidence

### Analysis Depth Score (0.0-1.0)
Rewards comprehensive reasoning:
- ✅ Issue has ≥1 evidence type
- ✅ Has REASONS_BASES or MEDICAL_OPINION passage
- ✅ Denial explains missing evidence
- ✅ Multiple passage types (thorough analysis)

### Usage
```bash
# Compute scores for all issues
python scripts/score_issues.py

# View scores in validation
python scripts/validate.py
```

### Files
- `src/scoring.py` - Scoring logic
- `scripts/score_issues.py` - Score runner
- `scripts/migrate_add_scores.py` - Migration for existing DBs

---

## Enhancement 2: LEGALBENCH-Style Validation Suite

### What It Does
Transforms the 5 MVP queries into a rigorous test suite with pass/fail gates.

### Tests

| Test | LEGALBENCH Category | Assertion |
|------|---------------------|-----------|
| Q1: Similarity | Interpretation | Returns relevant cases with passages |
| Q2: Evidence Chain | Rule-Application | Granted issues cite authority OR medical opinion |
| Q3: Denial Reasoning | Rule-Application (negative) | Denied issues explain missing evidence |
| Q4: Evidence Diff | Cross-Case Reasoning | Successfully compares patterns |
| Q5: Authority Stats | Rule-Recall Proxy | Authorities are properly formatted |

### Regression Prevention
Catches issues before they reach production:
- No empty evidence with confident outcomes
- Denied issues must list ≥1 missing element
- Granted issues must have supporting evidence

### Usage
```bash
# Run the validation suite
python scripts/validate_reasoning.py

# Use in CI/CD
python scripts/validate_reasoning.py || exit 1
```

### Files
- `scripts/validate_reasoning.py` - LEGALBENCH-style validator

---

## Enhancement 3: Rule-Recall Metadata

### What It Does
Explicitly captures when the model identifies legal rules (e.g., "38 C.F.R. § 3.310 – secondary service connection").

### Schema Changes
```python
class ExtractionResult(BaseModel):
    ...
    rule_recalled: Optional[str] = None
    rule_confidence: Optional[float] = None
```

### Why It Matters
- **Auditability**: Show which rule the AI thinks applies
- **Defensibility**: "How did you decide this?" → Point to explicit rule
- **Recruiter Demos**: "Look, it knows the regulation!"

### Future Enhancement
Populate this during extraction when rule is explicitly stated in text.

**Do NOT infer** - LEGALBENCH is strict about hallucinations.

### Files
- `src/extraction/models.py` - Added fields to `ExtractionResult`

---

## Enhancement 4: Rhetorical Understanding

### What It Does
Adds passage tags that capture **WHY** the VA said no (not just what's missing).

### New Passage Tags

| Tag | Meaning | Use Case |
|-----|---------|----------|
| `NEGATIVE_CREDIBILITY` | Board questions witness reliability | "Why did VA reject lay statement?" |
| `NO_NEXUS_FOUND` | No medical connection established | "Why was secondary claim denied?" |
| `BENEFIT_OF_DOUBT_APPLIED` | 38 C.F.R. § 3.102 invoked | "Did veteran get benefit of doubt?" |
| `WEIGHING_OF_EVIDENCE` | Board weighs competing evidence | "How did Board choose between exams?" |

### Original Tags (Still Supported)
- `MEDICAL_OPINION`
- `EXAM_ADEQUACY`
- `LAY_EVIDENCE`
- `REASONS_BASES`

### Why It Matters
Unlocks analysis like:
- "Compare VA reasoning styles across Regional Offices"
- "How often is benefit of doubt applied?"
- "Which judges most often cite negative credibility?"

### Future Enhancement
Add classification pass during extraction to tag rhetorical passages.

### Files
- `src/extraction/models.py` - Extended `ExtractedPassage.tag` enum

---

## Enhancement 5: Full Integration

### Workflow

```
1. Ingest decisions
   └─> python scripts/ingest.py

2. Run scoring
   └─> python scripts/score_issues.py

3. Validate schema + reasoning
   ├─> python scripts/validate.py
   └─> python scripts/validate_reasoning.py

4. Query with confidence
   └─> Use src/queries/* with scored data
```

### Query Integration
All queries now benefit from dual scores:

```python
# Example: Find high-quality similar cases
SELECT ... FROM issues
WHERE correctness_score > 0.8
  AND analysis_depth_score > 0.7
ORDER BY similarity DESC
```

---

## Migration Guide

### For Existing Databases

1. **Add score columns**:
   ```bash
   python scripts/migrate_add_scores.py
   ```

2. **Score existing issues**:
   ```bash
   python scripts/score_issues.py
   ```

3. **Validate**:
   ```bash
   python scripts/validate_reasoning.py
   ```

### For New Installations

The schema already includes score columns. Just run:
```bash
docker compose up -d
python scripts/ingest.py
python scripts/score_issues.py
```

---

## Comparison to LEGALBENCH

| LEGALBENCH | Our Implementation |
|------------|-------------------|
| Rule-Recall tasks | Q5: Authority stats + rule_recalled field |
| Rule-Application tasks | Q2: Evidence chain + Q3: Denial reasoning |
| Interpretation tasks | Q1: Similarity search |
| Rhetorical understanding | New passage tags (NEGATIVE_CREDIBILITY, etc.) |
| Cross-case reasoning | Q4: Evidence diff by outcome |
| Manual grading rubric | Automated dual-score evaluation |

---

## Future Enhancements

### 1. Judge-Level Pattern Analysis
Once we have rhetorical tags at scale:
```sql
SELECT judge_name, COUNT(*) as negative_credibility_count
FROM decisions d
JOIN passages p ON d.id = p.decision_id
WHERE p.tag = 'NEGATIVE_CREDIBILITY'
GROUP BY judge_name
```

### 2. Regional Office Comparison
```sql
SELECT regional_office,
       AVG(correctness_score) as avg_correctness,
       AVG(analysis_depth_score) as avg_analysis
FROM decisions d
JOIN issues i ON d.id = i.decision_id
GROUP BY regional_office
```

### 3. Rule Extraction During Ingestion
Add LLM step to extract `rule_recalled` from decision text:
- Prompt: "What legal regulation is being applied here?"
- Only populate if explicitly stated
- Add confidence threshold (e.g., 0.9+)

### 4. Confidence Calibration
Compare model confidence to actual correctness scores:
```python
# Are high-confidence extractions actually more correct?
correlation(passage.confidence, issue.correctness_score)
```

---

## Benefits

### 1. Defensible AI
"How did your system decide this?"
→ Point to specific rule, evidence chain, and reasoning scores

### 2. Continuous Validation
Catch regressions before deployment:
```bash
# In CI/CD
pytest tests/ && python scripts/validate_reasoning.py
```

### 3. Pattern Discovery
"What makes a strong PTSD claim?"
→ Query high-scoring granted issues for that condition

### 4. Recruiter-Friendly Demos
"Show me a well-reasoned grant"
→ Filter by `analysis_depth_score > 0.8`

---

## References

- LEGALBENCH Paper: [Link to paper if available]
- VA Regulations: 38 C.F.R. § 3.102 (Benefit of doubt)
- This System: `README.md` for architecture overview
