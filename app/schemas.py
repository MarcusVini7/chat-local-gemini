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


class StoreListItem(StoreOut):
    createdAt: str
    updatedAt: str


class StoreListResponse(BaseModel):
    items: list[StoreListItem]
    count: int


class StoreSummaryRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)


class StoreSummaryResponse(BaseModel):
    summary: str
    citations: list["Citation"]
    confidence: Confidence
    reason: str


class SuggestQuestionsRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)


class SuggestQuestionsResponse(BaseModel):
    questions: list[str]
    citations: list["Citation"]
    confidence: Confidence
    reason: str


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


class DocumentListItem(BaseModel):
    id: int
    storeId: int
    tenantId: str
    storeKey: str
    displayName: str
    originalFilename: str
    sha256: str
    mimeType: str | None = None
    sizeBytes: int
    geminiDocumentName: str | None = None
    status: str
    active: bool
    notes: str | None = None
    errorMessage: str | None = None
    createdAt: str
    indexedAt: str | None = None
    deletedAt: str | None = None
    replacedByDocumentId: int | None = None
    # Campos de integridade
    localFileExists: bool | None = None
    integrityStatus: str | None = None
    integrityCheckedAt: str | None = None
    integrityMessage: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    count: int


class DocumentUpdateRequest(BaseModel):
    notes: str | None = None
    active: bool | None = None


class DocumentReplaceResponse(BaseModel):
    replaced: bool
    oldDocumentId: int
    newDocument: DocumentUploadResponse


# ── Integridade ──────────────────────────────────────────────────────────────

class DocumentIntegrityResult(BaseModel):
    documentId: int
    originalFilename: str
    localPath: str | None = None
    localFileExists: bool
    integrityStatus: str
    integrityMessage: str
    integrityCheckedAt: str


class StoreIntegrityRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)


class StoreIntegritySummary(BaseModel):
    total: int
    ok: int
    missingLocalFile: int
    inactive: int
    remoteOnly: int
    failed: int


class StoreIntegrityItem(BaseModel):
    id: int
    originalFilename: str
    active: bool
    localFileExists: bool
    integrityStatus: str
    integrityMessage: str


class StoreIntegrityResponse(BaseModel):
    tenantId: str
    storeKey: str
    summary: StoreIntegritySummary
    items: list[StoreIntegrityItem]


# ── Rebuild plan ─────────────────────────────────────────────────────────────

class RebuildPlanRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)


class RebuildPlanItem(BaseModel):
    id: int
    originalFilename: str
    localPath: str | None = None
    integrityStatus: str | None = None


class RebuildPlanResponse(BaseModel):
    tenantId: str
    storeKey: str
    canRebuildSafely: bool
    reason: str
    activeAvailableDocuments: list[RebuildPlanItem]
    activeMissingDocuments: list[RebuildPlanItem]
    inactiveDocuments: list[RebuildPlanItem]


# ── Stats ─────────────────────────────────────────────────────────────────────

class StoreDocumentStats(BaseModel):
    total: int
    active: int
    inactive: int
    indexed: int
    failed: int
    uploaded: int


class StoreIntegrityStats(BaseModel):
    ok: int
    missingLocalFile: int
    remoteOnly: int
    unknown: int


class StoreQueryStats(BaseModel):
    total: int
    highConfidence: int
    lowConfidence: int
    shouldEscalate: int


class StoreNoteStats(BaseModel):
    total: int


class StoreStatsResponse(BaseModel):
    tenantId: str
    storeKey: str
    displayName: str
    documents: StoreDocumentStats
    queries: StoreQueryStats
    notes: StoreNoteStats
    integrity: StoreIntegrityStats | None = None


# ── Recursos extras (guia de estudos, FAQ, briefing, timeline) ────────────────────────

class StudyGuideRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    level: str = "intermediario"


class FaqRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)
    nQuestions: int = Field(default=10, ge=3, le=20)


class BriefingRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)
    audience: str = "executivo"


class TimelineRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)


class StudyFeatureResponse(BaseModel):
    content: str
    citations: list[Citation]
    confidence: Confidence
    reason: str


class QueryListItem(BaseModel):
    id: int
    storeId: int
    tenantId: str
    storeKey: str
    channel: str | None = None
    question: str
    answer: str
    confidence: str
    shouldEscalate: bool
    citations: list[Citation]
    createdAt: str


class QueryListResponse(BaseModel):
    items: list[QueryListItem]
    count: int


class NoteCreateRequest(BaseModel):
    tenantId: str = Field(min_length=1)
    storeKey: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    sourceType: str | None = None
    sourceQueryId: int | None = Field(default=None, gt=0)


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)


class NoteResponse(BaseModel):
    id: int
    storeId: int
    tenantId: str
    storeKey: str
    title: str
    content: str
    sourceType: str | None = None
    sourceQueryId: int | None = None
    createdAt: str
    updatedAt: str


class NotesListResponse(BaseModel):
    items: list[NoteResponse]
    count: int
