"""VKS Expert AI API schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(..., description="Engineering question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of retrieved sources")


class SourceInfo(BaseModel):
    document: str
    page: int
    score: float


class EvidenceInfo(BaseModel):
    confidence: float
    accepted: int
    rejected: int
    sufficient: bool


class AnswerResponse(BaseModel):
    question: str
    answer: str
    evidence_confidence: Optional[float] = None
    evidence_sufficient: Optional[bool] = None
    evidence: Optional[EvidenceInfo] = None
    sources: List[SourceInfo] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "VKS Expert AI"


class NormUploadResponse(BaseModel):
    success: bool
    document_id: str
    version_id: str
    number: str
    title: str
    status: str
    filename: str


class NormIndexResponse(BaseModel):
    success: bool
    document_id: str
    version_id: str
    status: str
    message: str


class NormDeleteResponse(BaseModel):
    success: bool
    document_id: str
    version_id: str
    document_removed: bool
    message: str
