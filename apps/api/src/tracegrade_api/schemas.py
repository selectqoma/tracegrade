from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SpanKind(str, Enum):
    llm = "llm"
    tool = "tool"
    retrieval = "retrieval"
    agent = "agent"
    other = "other"


# ---------------------------------------------------------------------------
# OTLP ingest
# ---------------------------------------------------------------------------


class OTLPAttribute(BaseModel):
    key: str
    value: dict[str, Any]


class OTLPEvent(BaseModel):
    time_unix_nano: int | None = None
    name: str
    attributes: list[OTLPAttribute] = Field(default_factory=list)


class OTLPStatus(BaseModel):
    code: int = 0
    message: str = ""


class OTLPSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    kind: int = 0
    start_time_unix_nano: int
    end_time_unix_nano: int
    attributes: list[OTLPAttribute] = Field(default_factory=list)
    events: list[OTLPEvent] = Field(default_factory=list)
    status: OTLPStatus = Field(default_factory=OTLPStatus)


class OTLPScopeSpans(BaseModel):
    spans: list[OTLPSpan] = Field(default_factory=list)


class OTLPResource(BaseModel):
    attributes: list[OTLPAttribute] = Field(default_factory=list)


class OTLPResourceSpans(BaseModel):
    resource: OTLPResource = Field(default_factory=OTLPResource)
    scope_spans: list[OTLPScopeSpans] = Field(default_factory=list)


class OTLPTrace(BaseModel):
    resource_spans: list[OTLPResourceSpans] = Field(default_factory=list)


class SessionMetadataUpdate(BaseModel):
    user_metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: uuid.UUID
    first_seen: datetime
    last_seen: datetime
    trace_count: int
    span_count: int
    total_cost_usd: float | None
    total_tokens_in: int | None
    total_tokens_out: int | None
    has_error: bool
    summary: str | None
    summary_model: str | None
    user_metadata: dict[str, Any] | None


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    next_cursor: str | None


# ---------------------------------------------------------------------------
# Traces & Spans
# ---------------------------------------------------------------------------


class SpanResponse(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None
    session_id: str | None
    name: str
    kind: str
    start_time: datetime
    end_time: datetime
    duration_ns: int
    status: str
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    tool_name: str | None
    attributes: dict[str, Any]
    events: list[dict[str, Any]]
    input: str | None
    output: str | None
    error: str | None
    children: list["SpanResponse"] = Field(default_factory=list)


SpanResponse.model_rebuild()


class TraceResponse(BaseModel):
    trace_id: str
    session_id: str | None
    root_spans: list[SpanResponse]


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class AnnotationCreate(BaseModel):
    target_type: str
    target_id: str
    author_id: uuid.UUID | None = None
    author_kind: str = "human"
    verdict: int | None = None
    failure_modes: list[str] | None = None
    note: str | None = None


class AnnotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: str
    target_id: str
    author_id: uuid.UUID | None
    author_kind: str
    verdict: int | None
    failure_modes: list[str] | None
    note: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Rubrics
# ---------------------------------------------------------------------------


class RubricCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    grader_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    source_annotation_ids: list[uuid.UUID] | None = None
    created_by: uuid.UUID | None = None


class RubricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    grader_type: str
    config: dict[str, Any]
    source_annotation_ids: list[uuid.UUID] | None
    created_by: uuid.UUID | None
    created_at: datetime


class RubricSynthesizeRequest(BaseModel):
    project_id: uuid.UUID
    name: str
    annotation_ids: list[uuid.UUID]
    grader_type: str = "llm_judge"


# ---------------------------------------------------------------------------
# Evals
# ---------------------------------------------------------------------------


class EvalCreate(BaseModel):
    suite_id: uuid.UUID
    name: str
    input_fixture: dict[str, Any] = Field(default_factory=dict)
    rubric_id: uuid.UUID
    expected: dict[str, Any] | None = None
    origin_trace_id: str | None = None
    version: int = 1
    enabled: bool = True


class EvalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    suite_id: uuid.UUID
    name: str
    input_fixture: dict[str, Any]
    rubric_id: uuid.UUID
    expected: dict[str, Any] | None
    origin_trace_id: str | None
    version: int
    enabled: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class RunCreate(BaseModel):
    agent_version: str | None = None
    triggered_by: str | None = None


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    suite_id: uuid.UUID
    agent_version: str | None
    triggered_by: str | None
    status: str
    passed: int
    failed: int
    regressed: int
    started_at: datetime | None
    finished_at: datetime | None


class RunReportResponse(RunResponse):
    report: dict[str, Any] | None
