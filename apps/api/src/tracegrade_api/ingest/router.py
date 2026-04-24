"""Ingest router: OTLP/HTTP JSON spans → ClickHouse + Postgres session upsert."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_project
from ..db import get_db
from ..models import Session
from ..schemas import OTLPTrace, SessionMetadataUpdate
from .buffer import NormalizedSpan, SpanBuffer

logger = logging.getLogger(__name__)

router = APIRouter()

_OTLP_KIND_MAP = {0: "other", 1: "other", 2: "other", 3: "llm", 4: "tool", 5: "retrieval"}


def _attr_value(value_dict: dict[str, Any]) -> Any:
    """Extract primitive from OTLP attribute value envelope."""
    for vtype in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if vtype in value_dict:
            return value_dict[vtype]
    if "arrayValue" in value_dict:
        return [_attr_value(v) for v in value_dict["arrayValue"].get("values", [])]
    if "kvlistValue" in value_dict:
        return {kv["key"]: _attr_value(kv["value"]) for kv in value_dict["kvlistValue"].get("values", [])}
    return None


def _flatten_attrs(otlp_attrs: list[Any]) -> dict[str, Any]:
    return {a.key: _attr_value(a.value) for a in otlp_attrs}


def _ns_to_dt(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)


def _parse_span(span: Any, resource_attrs: dict[str, Any]) -> NormalizedSpan:
    attrs = _flatten_attrs(span.attributes)
    events = [
        {
            "name": e.name,
            "time_unix_nano": e.time_unix_nano,
            "attributes": _flatten_attrs(e.attributes),
        }
        for e in span.events
    ]

    session_id = (
        attrs.get("gen_ai.session.id")
        or resource_attrs.get("gen_ai.session.id")
        or attrs.get("session.id")
        or resource_attrs.get("session.id")
    )

    # Derive kind from name or attrs
    raw_kind = attrs.get("span.kind") or attrs.get("gen_ai.operation.name") or ""
    kind_str = raw_kind.lower() if raw_kind else _OTLP_KIND_MAP.get(span.kind, "other")
    if "llm" in kind_str or "chat" in kind_str or "completion" in kind_str:
        kind_str = "llm"
    elif "tool" in kind_str:
        kind_str = "tool"
    elif "retriev" in kind_str or "embed" in kind_str:
        kind_str = "retrieval"
    elif "agent" in kind_str:
        kind_str = "agent"

    start = _ns_to_dt(span.start_time_unix_nano)
    end = _ns_to_dt(span.end_time_unix_nano)
    duration_ns = span.end_time_unix_nano - span.start_time_unix_nano

    status_str = "ok" if span.status.code in (0, 1) else "error"
    error_msg = span.status.message if span.status.code == 2 else None  # noqa: PLR2004

    model = attrs.get("gen_ai.request.model") or attrs.get("llm.model") or attrs.get("model")
    input_tokens = attrs.get("gen_ai.usage.input_tokens") or attrs.get("llm.token_count.prompt")
    output_tokens = attrs.get("gen_ai.usage.output_tokens") or attrs.get("llm.token_count.completion")
    cost_usd = attrs.get("gen_ai.usage.cost") or attrs.get("llm.cost_usd")
    tool_name = attrs.get("tool.name") or attrs.get("gen_ai.tool.name")

    input_text = attrs.get("gen_ai.prompt") or attrs.get("input") or attrs.get("llm.prompts")
    output_text = attrs.get("gen_ai.completion") or attrs.get("output") or attrs.get("llm.completions")
    if isinstance(input_text, (dict, list)):
        input_text = json.dumps(input_text)
    if isinstance(output_text, (dict, list)):
        output_text = json.dumps(output_text)

    return NormalizedSpan(
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        session_id=str(session_id) if session_id else None,
        name=span.name,
        kind=kind_str,
        start_time=start,
        end_time=end,
        duration_ns=duration_ns,
        status=status_str,
        model=str(model) if model else None,
        input_tokens=int(input_tokens) if input_tokens is not None else None,
        output_tokens=int(output_tokens) if output_tokens is not None else None,
        cost_usd=float(cost_usd) if cost_usd is not None else None,
        tool_name=str(tool_name) if tool_name else None,
        attributes=attrs,
        events=events,
        input=str(input_text) if input_text else None,
        output=str(output_text) if output_text else None,
        error=error_msg or None,
    )


async def _upsert_session(
    db: AsyncSession,
    project_id: uuid.UUID,
    session_id: str,
    spans: list[NormalizedSpan],
) -> None:
    has_error = any(s.status == "error" for s in spans)
    total_in = sum(s.input_tokens or 0 for s in spans)
    total_out = sum(s.output_tokens or 0 for s in spans)
    total_cost = sum(s.cost_usd or 0.0 for s in spans)
    first_start = min(s.start_time for s in spans)
    last_end = max(s.end_time for s in spans)

    stmt = (
        pg_insert(Session)
        .values(
            id=session_id,
            project_id=project_id,
            first_seen=first_start,
            last_seen=last_end,
            trace_count=1,
            span_count=len(spans),
            total_cost_usd=total_cost or None,
            total_tokens_in=total_in or None,
            total_tokens_out=total_out or None,
            has_error=has_error,
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "last_seen": text("GREATEST(sessions.last_seen, EXCLUDED.last_seen)"),
                "first_seen": text("LEAST(sessions.first_seen, EXCLUDED.first_seen)"),
                "trace_count": text("sessions.trace_count + 1"),
                "span_count": text("sessions.span_count + EXCLUDED.span_count"),
                "total_cost_usd": text("COALESCE(sessions.total_cost_usd, 0) + COALESCE(EXCLUDED.total_cost_usd, 0)"),
                "total_tokens_in": text("COALESCE(sessions.total_tokens_in, 0) + COALESCE(EXCLUDED.total_tokens_in, 0)"),
                "total_tokens_out": text("COALESCE(sessions.total_tokens_out, 0) + COALESCE(EXCLUDED.total_tokens_out, 0)"),
                "has_error": text("sessions.has_error OR EXCLUDED.has_error"),
            },
        )
    )
    await db.execute(stmt)
    await db.commit()


@router.post("/v1/traces", status_code=status.HTTP_202_ACCEPTED)
async def ingest_traces(
    payload: OTLPTrace,
    background_tasks: BackgroundTasks,
    request: Request,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    buffer: SpanBuffer = request.app.state.span_buffer

    all_spans: list[NormalizedSpan] = []
    for resource_spans in payload.resource_spans:
        resource_attrs = _flatten_attrs(resource_spans.resource.attributes)
        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                try:
                    normalized = _parse_span(span, resource_attrs)
                    all_spans.append(normalized)
                except Exception:
                    logger.exception("Failed to parse span %s", getattr(span, "span_id", "?"))

    # Group spans by session and upsert
    sessions: dict[str, list[NormalizedSpan]] = {}
    for span in all_spans:
        if span.session_id:
            sessions.setdefault(span.session_id, []).append(span)

    async def write_to_clickhouse() -> None:
        for span in all_spans:
            await buffer.add(span)
        for sid, sid_spans in sessions.items():
            try:
                await _upsert_session(db, project_id, sid, sid_spans)
            except Exception:
                logger.exception("Failed to upsert session %s", sid)

    background_tasks.add_task(write_to_clickhouse)

    return {"accepted": len(all_spans)}


@router.post("/v1/ingest/session/{session_id}/metadata", status_code=status.HTTP_200_OK)
async def update_session_metadata(
    session_id: str,
    body: SessionMetadataUpdate,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from sqlalchemy import select

    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.project_id == project_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = session.user_metadata or {}
    existing.update(body.user_metadata)
    session.user_metadata = existing
    await db.commit()
    return {"ok": True}
