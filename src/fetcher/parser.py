import re
from datetime import datetime
from typing import Optional

# Date patterns
DATE_PATTERNS = [
    re.compile(r"Decision\s*Date\s*[:\-]\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", re.I),
    re.compile(r"DATE:\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", re.I),
]

DOCKET_RE = re.compile(r"DOCKET\s*NO\.?\s*[:\-]?\s*([\d\-]+)", re.I)

OUTCOME_PATTERNS = [
    ("Granted", re.compile(r"\bORDER\b.*?\b(is\s+)?GRANTED\b", re.I | re.S)),
    ("Denied", re.compile(r"\bORDER\b.*?\b(is\s+)?DENIED\b", re.I | re.S)),
    ("Remanded", re.compile(r"\b(is\s+)?REMANDED\b", re.I)),
]

CFR_RE = re.compile(r"38\s*C?\.?F?\.?R?\.?\s*[§]?\s*([\d]+\.[\d]+[a-z0-9\(\)]*)", re.I)
RO_RE = re.compile(r"Regional\s+Office\s+in\s+([A-Za-z\s,]+?)(?:\.|,?\s*(?:in|has|the|$))", re.I)
JUDGE_RE = re.compile(r"(?:Veterans\s+Law\s+Judge|Acting\s+Veterans\s+Law\s+Judge)[,:\s]+([A-Z][a-zA-Z\.\s\-]+?)(?:\n|,\s*(?:Chair|Member)|$)", re.I)

def parse_decision(text: str) -> dict:
    """Parse BVA decision text and extract structured metadata."""
    result = {
        "decision_date": None,
        "docket_no": None,
        "outcome": None,
        "issues": [],
        "citations": [],
        "regional_office": None,
        "judge": None,
        "system_type": None,
    }

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Decision date
    for pattern in DATE_PATTERNS:
        if m := pattern.search(text):
            try:
                result["decision_date"] = datetime.strptime(
                    m.group(1), "%B %d, %Y"
                ).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    # Docket number
    if m := DOCKET_RE.search(text):
        result["docket_no"] = m.group(1).strip()

    # Outcome detection
    upper_text = text.upper()
    order_match = re.search(r"ORDER\s*(.*?)(?=FINDING|REMAND|CONCLUSION|\Z)", text, re.I | re.S)
    if order_match:
        order_text = order_match.group(1).upper()
        has_granted = "GRANTED" in order_text
        has_denied = "DENIED" in order_text
        has_remanded = "REMANDED" in order_text or "REMANDED" in upper_text[:2000]

        if sum([has_granted, has_denied, has_remanded]) > 1:
            result["outcome"] = "Mixed"
        elif has_granted:
            result["outcome"] = "Granted"
        elif has_denied:
            result["outcome"] = "Denied"
        elif has_remanded:
            result["outcome"] = "Remanded"

    # Issues - look for "Entitlement to..." patterns
    issue_matches = re.findall(r"(Entitlement\s+to\s+[^\.]+\.)", text, re.I)
    seen = set()
    for issue in issue_matches[:10]:
        clean = re.sub(r"\s+", " ", issue).strip()
        if clean not in seen and len(clean) > 20:
            seen.add(clean)
            result["issues"].append(clean)
    result["issues"] = result["issues"][:5]

    # Citations
    cfrs = CFR_RE.findall(text)
    result["citations"] = sorted(set([f"38 C.F.R. § {c}" for c in cfrs[:15]]))

    # Regional office
    if m := RO_RE.search(text):
        ro = m.group(1).strip().rstrip(".,")
        ro = re.sub(r"\s+(in|has|the)$", "", ro, flags=re.I)
        if len(ro) > 3:
            result["regional_office"] = ro

    # Judge
    if m := JUDGE_RE.search(text):
        judge = m.group(1).strip().rstrip(".,")
        if judge and not judge.upper().startswith("BOARD") and len(judge) > 3:
            result["judge"] = judge

    # System type (AMA vs Legacy)
    if "AMA" in upper_text or "APPEALS MODERNIZATION" in upper_text:
        result["system_type"] = "AMA"
    elif "LEGACY" in upper_text or "OLD SYSTEM" in upper_text:
        result["system_type"] = "Legacy"

    return result
