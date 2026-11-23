"""Request and response models for analyses, history and model status."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    headline: str | None = Field(default=None, max_length=500)
    text: str = Field(min_length=1, description="The article body to analyse.")


class UrlAnalysisRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1000, description="The web address of the article. Only http(s) pages on public websites are read.")


class EvidenceRequest(BaseModel):
    text: str = Field(min_length=10, max_length=5000, description="A claim, or a passage from which up to five claims are picked.")


class ModelInfo(BaseModel):
    module: str
    name: str
    version: str
    status: str


class AnalysisOut(BaseModel):
    id: int
    analysis_type: str
    verdict: str
    # The model's probability for the class it leans towards. It is NOT the probability that the news is true.
    confidence: float | None = None
    status: str
    headline: str | None = None
    source_filename: str | None = None
    source_url: str | None = None  # url analyses: the address that was submitted
    submitted_text: str | None = None  # only on the detail view, and only for the owner
    created_at: datetime
    model: ModelInfo | None = None
    details: dict[str, Any] | None = None
    limitations: str | None = None
    is_demo: bool = False
    has_heatmap: bool = False


class AnalysisPage(BaseModel):
    items: list[AnalysisOut]
    total: int
    page: int
    page_size: int


class FeedbackCreate(BaseModel):
    category: str = Field(pattern=r"^(bug|incorrect_result|feature_request|other)$")
    message: str = Field(min_length=5, max_length=2000)
    analysis_id: int | None = None


class FeedbackOut(BaseModel):
    id: int
    analysis_id: int | None
    category: str
    message: str
    status: str
    created_at: datetime
    user_id: int | None = None
    username: str | None = None


class FeedbackReview(BaseModel):
    status: str = Field(pattern=r"^(new|reviewed|dismissed)$")


class AdminUserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(user|admin)$")
    is_active: bool | None = None
