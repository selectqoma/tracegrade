import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_project
from ..db import get_clickhouse, get_db
from ..models import Annotation, Session
from ..schemas import SessionListResponse, SessionResponse, SpanResponse, TraceResponse

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(None, description="Search sessions"),
    failure_mode: str | None = Query(None),
    has_error: bool | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, le=100),
):
    stmt = select(Session).where(Session.project_id == project_id)

    if has_error is not None:
        stmt = stmt.where(Session.has_error == has_error)

    if q:
        stmt = stmt.where(Session.id.ilike(f"%{q}%"))

    if failure_mode:
        # Join with annotations to filter by failure mode
        stmt = stmt.join(
            Annotation,
            (Annotation.target_type == "session") & (Annotation.target_id == Session.id),
        ).where(Annotation.failure_modes.any(failure_mode))

    if cursor:
        stmt = stmt.where(Session.last_seen < cursor)

    stmt = stmt.order_by(Session.last_seen.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    sessions = list(result.scalars().all())

    next_cursor = None
    if len(sessions) > limit:
        sessions = sessions[:limit]
        next_cursor = sessions[-1].last_seen.isoformat()

    return SessionListResponse(
        items=[SessionResponse.model_validate(s) for s in sessions],
        next_cursor=next_cursor,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.project_id == project_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/timeline")
async def get_session_timeline(
    session_id: str,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TraceResponse]:
    # Verify session belongs to project
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.project_id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    ch = get_clickhouse()
    rows = ch.query(
        "SELECT * FROM spans WHERE session_id = {sid:String} ORDER BY start_time",
        parameters={"sid": session_id},
    )

    # Group by trace_id and build trees
    traces: dict[str, list[dict]] = {}
    for row in rows.named_results():
        row_dict = dict(row)
        row_dict["attributes"] = json.loads(row_dict.get("attributes", "{}"))
        row_dict["events"] = json.loads(row_dict.get("events", "[]"))
        trace_id = row_dict["trace_id"]
        traces.setdefault(trace_id, []).append(row_dict)

    result_traces = []
    for trace_id, spans in traces.items():
        root_spans = _build_span_tree(spans)
        result_traces.append(TraceResponse(
            trace_id=trace_id,
            session_id=session_id,
            root_spans=root_spans,
        ))

    return result_traces


def _build_span_tree(spans: list[dict]) -> list[SpanResponse]:
    by_id: dict[str, SpanResponse] = {}
    for s in spans:
        by_id[s["span_id"]] = SpanResponse(
            trace_id=s["trace_id"],
            span_id=s["span_id"],
            parent_span_id=s.get("parent_span_id") or None,
            session_id=s.get("session_id") or None,
            name=s["name"],
            kind=s["kind"],
            start_time=s["start_time"],
            end_time=s["end_time"],
            duration_ns=s.get("duration_ns", 0),
            status=s["status"],
            model=s.get("model") or None,
            input_tokens=s.get("input_tokens"),
            output_tokens=s.get("output_tokens"),
            cost_usd=s.get("cost_usd"),
            tool_name=s.get("tool_name") or None,
            attributes=s.get("attributes", {}),
            events=s.get("events", []),
            input=s.get("input") or None,
            output=s.get("output") or None,
            error=s.get("error") or None,
        )

    roots = []
    for span in by_id.values():
        parent_id = span.parent_span_id
        if parent_id and parent_id in by_id:
            by_id[parent_id].children.append(span)
        else:
            roots.append(span)

    return roots
