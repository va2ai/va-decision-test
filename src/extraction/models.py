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
    tag: str  # MEDICAL_OPINION, EXAM_ADEQUACY, LAY_EVIDENCE, REASONS_BASES
    confidence: float = 0.7

class ExtractionResult(BaseModel):
    issues: list[ExtractedIssue] = Field(default_factory=list)
    authorities: list[str] = Field(default_factory=list)
    passages: list[ExtractedPassage] = Field(default_factory=list)
    system_type: Optional[str] = None
