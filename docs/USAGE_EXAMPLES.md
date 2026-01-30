# Usage Examples: LEGALBENCH Enhancements

## Quick Start: Score and Validate

```bash
# 1. Run ingestion
python scripts/ingest.py --limit 20

# 2. Score all issues
python scripts/score_issues.py

# 3. Run validation suite
python scripts/validate_reasoning.py
```

Expected output:
```
============================================================
LEGALBENCH-STYLE REASONING VALIDATION
============================================================

=== Q1: Similarity (Interpretation + Reasoning) ===
  ✓ Found similar cases for query
  ✓ Similar cases include passage content (not just IDs)

=== Q2: Evidence Chain (Fact → Element) ===
  ✓ All granted issues cite authority OR medical opinion (violations: 0/5)

=== Q3: Denial Reasoning (Negative Case) ===
  ✓ All denied issues explain missing evidence (violations: 0/3)
  ✓ No confident outcomes without evidence (violations: 0)

...

RESULTS: 12/12 assertions passed (100.0%)
✓ ALL LEGALBENCH-STYLE RULES SATISFIED
  System demonstrates correct reasoning patterns
```

---

## Find High-Quality Cases

```python
from src.db.connection import get_connection

conn = get_connection()

# Find well-reasoned granted decisions
cur = conn.execute("""
    SELECT
        i.id,
        i.issue_text,
        c.name as condition,
        i.correctness_score,
        i.analysis_depth_score
    FROM issues i
    LEFT JOIN issue_conditions ic ON i.id = ic.issue_id
    LEFT JOIN conditions c ON ic.condition_id = c.id
    WHERE i.outcome = 'Granted'
      AND i.correctness_score > 0.8
      AND i.analysis_depth_score > 0.7
    ORDER BY (i.correctness_score + i.analysis_depth_score) DESC
    LIMIT 10
""")

for row in cur.fetchall():
    print(f"Issue {row[0]}: {row[2]} - Correctness: {row[3]:.3f}, Analysis: {row[4]:.3f}")
```

---

## Identify Extraction Errors

```python
# Find issues with low correctness scores
cur = conn.execute("""
    SELECT
        i.id,
        i.issue_text,
        i.outcome,
        i.correctness_score
    FROM issues i
    WHERE i.correctness_score < 0.5
    ORDER BY i.correctness_score ASC
    LIMIT 5
""")

print("Issues with potential extraction errors:")
for row in cur.fetchall():
    print(f"  Issue {row[0]}: {row[2]} - Score: {row[3]:.3f}")
    print(f"    Text: {row[1][:100]}...")
```

---

## Compare Evidence Quality by Outcome

```python
from src.queries.q4_evidence_diff import compare_evidence_by_outcome

diff = compare_evidence_by_outcome(conn, "tinnitus")

# Analyze which evidence types appear more in grants vs denials
granted = {d['evidence_type']: d['count'] for d in diff if d['outcome'] == 'Granted'}
denied = {d['evidence_type']: d['count'] for d in diff if d['outcome'] == 'Denied'}

print("Evidence patterns for tinnitus:")
print(f"  Granted: {granted}")
print(f"  Denied: {denied}")

# What evidence is more common in grants?
for ev_type in granted:
    if ev_type in denied:
        ratio = granted[ev_type] / denied[ev_type]
        if ratio > 1.5:
            print(f"  ✓ {ev_type} appears {ratio:.1f}x more in grants")
```

---

## Audit Denial Reasoning

```python
from src.queries.q3_denial_why import analyze_denial

# Get all denied issues
cur = conn.execute("SELECT id FROM issues WHERE outcome = 'Denied'")
denied_ids = [row[0] for row in cur.fetchall()]

print(f"Analyzing {len(denied_ids)} denied issues...\n")

# Check which have explicit reasoning
well_explained = 0
poorly_explained = 0

for issue_id in denied_ids:
    analysis = analyze_denial(conn, issue_id)

    has_missing = len(analysis['missing_evidence']) > 0
    has_exam_passage = len(analysis['exam_passages']) > 0

    if has_missing or has_exam_passage:
        well_explained += 1
    else:
        poorly_explained += 1
        print(f"  ⚠ Issue {issue_id}: No clear explanation for denial")

print(f"\nSummary:")
print(f"  Well-explained: {well_explained}/{len(denied_ids)}")
print(f"  Poorly-explained: {poorly_explained}/{len(denied_ids)}")
```

---

## Query with Rhetorical Tags

```python
# Find denials with explicit "no nexus" reasoning
cur = conn.execute("""
    SELECT
        i.id,
        i.issue_text,
        c.name as condition,
        p.text as passage
    FROM issues i
    JOIN issue_passages ip ON i.id = ip.issue_id
    JOIN passages p ON ip.passage_id = p.id
    LEFT JOIN issue_conditions ic ON i.id = ic.issue_id
    LEFT JOIN conditions c ON ic.condition_id = c.id
    WHERE i.outcome = 'Denied'
      AND p.tag = 'NO_NEXUS_FOUND'
    LIMIT 5
""")

print("Denials with explicit 'no nexus' reasoning:")
for row in cur.fetchall():
    print(f"\nIssue {row[0]}: {row[2]}")
    print(f"  Passage: {row[3][:200]}...")
```

---

## Batch Score New Ingestions

```python
from src.scoring import compute_correctness_score, compute_analysis_depth_score

# Score a single new issue
new_issue_id = 123

correctness = compute_correctness_score(conn, new_issue_id)
analysis = compute_analysis_depth_score(conn, new_issue_id)

# Update database
conn.execute("""
    UPDATE issues
    SET correctness_score = %s, analysis_depth_score = %s
    WHERE id = %s
""", (correctness, analysis, new_issue_id))
conn.commit()

print(f"Issue {new_issue_id}:")
print(f"  Correctness: {correctness:.3f}")
print(f"  Analysis Depth: {analysis:.3f}")

if correctness < 0.6:
    print("  ⚠ Low correctness - possible extraction error")
if analysis < 0.5:
    print("  ℹ Low analysis depth - minimal reasoning detected")
```

---

## CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Run Ingestion
  run: python scripts/ingest.py --limit 100

- name: Score Issues
  run: python scripts/score_issues.py

- name: Validate Reasoning
  run: |
    python scripts/validate_reasoning.py
    if [ $? -ne 0 ]; then
      echo "Reasoning validation failed!"
      exit 1
    fi
```

This prevents deploying models with poor reasoning patterns.

---

## Debugging Low Scores

```python
# Investigate why an issue has low correctness
issue_id = 42

cur = conn.execute("""
    SELECT i.outcome, i.issue_text, d.raw_text
    FROM issues i
    JOIN decisions d ON i.decision_id = d.id
    WHERE i.id = %s
""", (issue_id,))

outcome, issue_text, decision_text = cur.fetchone()

print(f"Issue {issue_id}: {outcome}")
print(f"Text: {issue_text}\n")

# Check evidence vs passages
cur = conn.execute("""
    SELECT COUNT(*) FROM issue_evidence WHERE issue_id = %s
""", (issue_id,))
evidence_count = cur.fetchone()[0]

cur = conn.execute("""
    SELECT COUNT(*) FROM issue_passages WHERE issue_id = %s
""", (issue_id,))
passage_count = cur.fetchone()[0]

print(f"Evidence types: {evidence_count}")
print(f"Passages: {passage_count}")

if evidence_count > 0 and passage_count == 0:
    print("❌ PROBLEM: Evidence claimed but no passages tagged!")
    print("   This will lower correctness score.")

# Check authorities
cur = conn.execute("""
    SELECT a.citation FROM authorities a
    JOIN decision_authorities da ON a.id = da.authority_id
    JOIN issues i ON da.decision_id = i.decision_id
    WHERE i.id = %s
""", (issue_id,))

authorities = [row[0] for row in cur.fetchall()]
print(f"\nAuthorities cited: {len(authorities)}")

for auth in authorities:
    if auth not in decision_text:
        print(f"❌ PROBLEM: Authority '{auth}' not found in decision text!")
```

---

## Report Generation

```python
# Generate a quality report
cur = conn.execute("""
    SELECT
        COUNT(*) as total_issues,
        AVG(correctness_score) as avg_correctness,
        AVG(analysis_depth_score) as avg_analysis,
        COUNT(*) FILTER (WHERE correctness_score >= 0.8) as high_correctness,
        COUNT(*) FILTER (WHERE analysis_depth_score >= 0.7) as high_analysis
    FROM issues
    WHERE correctness_score IS NOT NULL
""")

row = cur.fetchone()
total, avg_c, avg_a, high_c, high_a = row

print("=" * 60)
print("EXTRACTION QUALITY REPORT")
print("=" * 60)
print(f"\nTotal Issues: {total}")
print(f"Average Correctness: {avg_c:.3f}")
print(f"Average Analysis Depth: {avg_a:.3f}")
print(f"\nHigh-Quality Issues:")
print(f"  Correctness ≥0.8: {high_c} ({high_c/total*100:.1f}%)")
print(f"  Analysis ≥0.7: {high_a} ({high_a/total*100:.1f}%)")

# By outcome
cur = conn.execute("""
    SELECT
        outcome,
        COUNT(*) as count,
        AVG(correctness_score) as avg_correctness,
        AVG(analysis_depth_score) as avg_analysis
    FROM issues
    WHERE correctness_score IS NOT NULL
    GROUP BY outcome
""")

print("\nBy Outcome:")
for row in cur.fetchall():
    outcome, count, avg_c, avg_a = row
    print(f"  {outcome}: {count} issues (C: {avg_c:.3f}, A: {avg_a:.3f})")
```

---

## Next Steps

- See [LEGALBENCH_ENHANCEMENTS.md](LEGALBENCH_ENHANCEMENTS.md) for detailed documentation
- Run `scripts/validate_reasoning.py` to ensure system quality
- Query scored data for pattern discovery
- Integrate scoring into your CI/CD pipeline
