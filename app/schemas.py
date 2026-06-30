from typing import Any, Literal

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]


class StoreCreate(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)
    displayName: str = Field(min_length=1)


class StoreOut(BaseModel):
    id: int
    tenantId: str
    storeKey: str
    displayName: str
    geminiStoreName: str


class Citation(BaseModel):
    source: str
    page: int | None = None
    snippet: str | None = None


class QueryRequest(BaseModel):
    tenantId: str
    storeKey: str
    question: str = Field(min_length=1)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Confidence
    reason: str


class CustomerAnswerRequest(BaseModel):
    tenantId: str
    channel: Literal["whatsapp", "email"] | str
    storeKey: str
    customerMessage: str = Field(min_length=1)
    ticketContext: dict[str, Any] = Field(default_factory=dict)
    style: str = "atendimento_whatsapp"


class CustomerAnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Confidence
    shouldEscalate: bool
    reason: str


class DocumentUploadResponse(BaseModel):
    id: int
    storeId: int
    originalFilename: str
    sha256: str
    status: str
    geminiDocumentName: str | None = None
    duplicate: bool = False
