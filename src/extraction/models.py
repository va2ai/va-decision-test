from pydantic import BaseModel, Field
from typing import Optional

class ExtractedIssue(BaseModel):
    issue_text: str
    outcome: str  # Granted, Denied, Remanded, Mixed
    connection_type: Optional[str] = None  # Direct, Secondary, Aggravation
    condition: Optional[str] = None
    evidence_types: list[str] = Field(default_factory=list)
    provider_types: list[str] = Field(default_factory=list)

class ExtractedPassage(BaseModel):
    text: str
    tag: str  # MEDICAL_OPINION, EXAM_ADEQUACY, LAY_EVIDENCE, REASONS_BASES, NEGATIVE_CREDIBILITY, NO_NEXUS_FOUND, BENEFIT_OF_DOUBT_APPLIED, WEIGHING_OF_EVIDENCE
    confidence: float = 0.7

class ExtractionResult(BaseModel):
    issues: list[ExtractedIssue] = Field(default_factory=list)
    authorities: list[str] = Field(default_factory=list)
    passages: list[ExtractedPassage] = Field(default_factory=list)
    system_type: Optional[str] = None
    rule_recalled: Optional[str] = None  # Legal rule explicitly stated (e.g., "38 C.F.R. § 3.310")
    rule_confidence: Optional[float] = None  # Confidence that rule was accurately identified
