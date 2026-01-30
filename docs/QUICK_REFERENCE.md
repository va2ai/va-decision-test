# LEGALBENCH Enhancements - Quick Reference

## Passage Tags

### Original Tags
| Tag | Use Case | Example |
|-----|----------|---------|
| `MEDICAL_OPINION` | Doctor's expert opinion | "The examiner opined that..." |
| `EXAM_ADEQUACY` | VA exam quality issues | "The exam was inadequate because..." |
| `LAY_EVIDENCE` | Veteran/buddy statements | "The veteran reported..." |
| `REASONS_BASES` | Board's reasoning | "The Board finds..." |

### New Rhetorical Tags
| Tag | Use Case | Example |
|-----|----------|---------|
| `NEGATIVE_CREDIBILITY` | Questions witness reliability | "The Board finds the statement not credible because..." |
| `NO_NEXUS_FOUND` | No medical connection | "The examiner found no nexus between..." |
| `BENEFIT_OF_DOUBT_APPLIED` | 38 CFR 3.102 invoked | "Resolving reasonable doubt in favor of..." |
| `WEIGHING_OF_EVIDENCE` | Competing evidence compared | "The Board gives greater weight to..." |

---

## Scoring Criteria

### Correctness Score (0.0 - 1.0)

**Start at 1.0, apply penalties:**

| Violation | Penalty | Reason |
|-----------|---------|--------|
| Evidence claimed, no passages | -0.3 | Claimed evidence must be quoted |
| Authority not in text | -0.15 | Citations must appear in decision |
| Granted without evidence | -0.4 | Grants require supporting facts |
| Denied with strong evidence | -0.1 | Suspicious but might be legitimate |

**Interpretation:**
- `≥ 0.8` - High quality extraction
- `0.6 - 0.8` - Acceptable
- `< 0.6` - Potential extraction error

### Analysis Depth Score (0.0 - 1.0)

**Start at 0.0, earn points:**

| Achievement | Points | Reason |
|-------------|--------|--------|
| Has ≥1 evidence type | +0.3 | Shows factual grounding |
| Has REASONS_BASES or MEDICAL_OPINION | +0.3 | Shows reasoning |
| Denial has explanation | +0.2 | Denials must explain why |
| ≥3 distinct passage types | +0.2 | Thorough analysis |

**Interpretation:**
- `≥ 0.7` - Comprehensive reasoning
- `0.5 - 0.7` - Moderate analysis
- `< 0.5` - Minimal reasoning detected

---

## Scripts Reference

```bash
# Migration (if upgrading existing DB)
python scripts/migrate_add_scores.py

# Score all issues
python scripts/score_issues.py

# Validate schema (basic)
python scripts/validate.py

# Validate reasoning (LEGALBENCH-style)
python scripts/validate_reasoning.py

# Full workflow
python scripts/ingest.py --limit 20
python scripts/score_issues.py
python scripts/validate_reasoning.py
```

---

## SQL Quick Queries

### Find High-Quality Issues
```sql
SELECT id, outcome, correctness_score, analysis_depth_score
FROM issues
WHERE correctness_score > 0.8
  AND analysis_depth_score > 0.7
ORDER BY (correctness_score + analysis_depth_score) DESC;
```

### Find Extraction Errors
```sql
SELECT id, outcome, correctness_score
FROM issues
WHERE correctness_score < 0.6
ORDER BY correctness_score ASC;
```

### Check Denial Reasoning Quality
```sql
SELECT
    i.id,
    i.correctness_score,
    i.analysis_depth_score,
    COUNT(DISTINCT p.tag) as reasoning_tag_count
FROM issues i
LEFT JOIN issue_passages ip ON i.id = ip.issue_id
LEFT JOIN passages p ON ip.passage_id = p.id
WHERE i.outcome = 'Denied'
GROUP BY i.id
HAVING COUNT(DISTINCT p.tag) < 2;
```

### Rhetorical Tags Usage
```sql
SELECT tag, COUNT(*) as count
FROM passages
WHERE tag IN (
    'NEGATIVE_CREDIBILITY',
    'NO_NEXUS_FOUND',
    'BENEFIT_OF_DOUBT_APPLIED',
    'WEIGHING_OF_EVIDENCE'
)
GROUP BY tag
ORDER BY count DESC;
```

---

## LEGALBENCH Mapping

| LEGALBENCH Category | Our Implementation |
|---------------------|-------------------|
| Rule-Recall | `rule_recalled` field + Q5: Authority Stats |
| Rule-Application (positive) | Q2: Evidence Chain + correctness score |
| Rule-Application (negative) | Q3: Denial Reasoning + analysis score |
| Interpretation | Q1: Similarity Search |
| Rhetorical Understanding | New passage tags |
| Cross-Case Reasoning | Q4: Evidence Diff |

---

## Integration Checklist

- [ ] Run migration on existing DB
- [ ] Score all issues after ingestion
- [ ] Add `validate_reasoning.py` to CI/CD
- [ ] Update extraction prompt to populate `rule_recalled`
- [ ] Train LLM to tag rhetorical passages
- [ ] Set up monitoring for low scores
- [ ] Document scoring thresholds for your use case

---

## Troubleshooting

**Q: Scores are all null**
A: Run `python scripts/migrate_add_scores.py` then `python scripts/score_issues.py`

**Q: All correctness scores are low**
A: Check extraction quality. Likely issues:
- Authorities extracted but not in text
- Evidence claimed without passages
- Run debug query in USAGE_EXAMPLES.md

**Q: All analysis scores are low**
A: Extraction may not be capturing passages. Check:
- Is `REASONS_BASES` being tagged?
- Are evidence types being detected?

**Q: validate_reasoning.py fails**
A: This is expected! It's finding real issues. Investigate:
1. Which assertions failed?
2. Are there systematic extraction errors?
3. Do you need to adjust extraction prompts?

---

## Support

- Full docs: [LEGALBENCH_ENHANCEMENTS.md](LEGALBENCH_ENHANCEMENTS.md)
- Examples: [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)
- Main README: [../README.md](../README.md)
