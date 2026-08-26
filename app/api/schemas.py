"""
VKS Expert AI
API Schemas v1

Purpose:
Pydantic models for FastAPI API.

Contains:
- Request models
- Response models
- Source information
- Evidence information
"""


from typing import List, Optional

from pydantic import BaseModel, Field



# ==========================================================
# Request models
# ==========================================================


class QuestionRequest(BaseModel):
    """
    User question request.
    """

    question: str = Field(
        ...,
        description="Engineering question",
        examples=[
            "Как определяется максимальный расчетный расход воды?"
        ]
    )


    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of retrieved sources"
    )



# ==========================================================
# Source models
# ==========================================================


class SourceInfo(BaseModel):
    """
    Retrieved normative source.
    """


    document: str = Field(
        ...,
        description="Document name"
    )


    page: int = Field(
        ...,
        description="Page number"
    )


    score: float = Field(
        ...,
        description="Similarity score"
    )



# ==========================================================
# Evidence models
# ==========================================================


class EvidenceInfo(BaseModel):
    """
    Evidence validation result.
    """


    confidence: float = Field(
        ...,
        description="Evidence confidence score"
    )


    accepted: int = Field(
        ...,
        description="Accepted evidence fragments"
    )


    rejected: int = Field(
        ...,
        description="Rejected evidence fragments"
    )


    sufficient: bool = Field(
        ...,
        description="Evidence sufficiency flag"
    )



# ==========================================================
# Response models
# ==========================================================


class AnswerResponse(BaseModel):
    """
    Final VKS Expert AI answer.
    """


    question: str = Field(
        ...,
        description="Original question"
    )


    answer: str = Field(
        ...,
        description="Technical answer"
    )


    evidence_confidence: Optional[float] = Field(
        default=None,
        description="Evidence confidence"
    )


    evidence_sufficient: Optional[bool] = Field(
        default=None,
        description="Evidence availability"
    )


    evidence: Optional[EvidenceInfo] = Field(
        default=None,
        description="Detailed evidence information"
    )


    sources: List[SourceInfo] = Field(
        default_factory=list,
        description="Normative sources"
    )



# ==========================================================
# Health response
# ==========================================================


class HealthResponse(BaseModel):
    """
    API health status.
    """


    status: str = Field(
        default="ok"
    )


    service: str = Field(
        default="VKS Expert AI"
    )
    