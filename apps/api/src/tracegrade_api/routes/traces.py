import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_project
from ..db import get_clickhouse, get_db
from ..schemas import SpanResponse, TraceResponse

router = APIRouter(prefix="/api", tags=["traces"])


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ch = get_clickhouse()
    rows = ch.query(
        "SELECT * FROM spans WHERE trace_id = {tid:String} ORDER BY start_time",
        parameters={"tid": trace_id},
    )

    spans = []
    session_id = None
    for row in rows.named_results():
        row_dict = dict(row)
        row_dict["attributes"] = json.loads(row_dict.get("attributes", "{}"))
        row_dict["events"] = json.loads(row_dict.get("events", "[]"))
        if not session_id and row_dict.get("session_id"):
            session_id = row_dict["session_id"]
        spans.append(row_dict)

    if not spans:
        raise HTTPException(status_code=404, detail="Trace not found")

    from .sessions import _build_span_tree
    root_spans = _build_span_tree(spans)

    return TraceResponse(trace_id=trace_id, session_id=session_id, root_spans=root_spans)


@router.get("/spans/{span_id}", response_model=SpanResponse)
async def get_span(
    span_id: str,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ch = get_clickhouse()
    rows = ch.query(
        "SELECT * FROM spans WHERE span_id = {sid:String} LIMIT 1",
        parameters={"sid": span_id},
    )

    result = list(rows.named_results())
    if not result:
        raise HTTPException(status_code=404, detail="Span not found")

    row = dict(result[0])
    row["attributes"] = json.loads(row.get("attributes", "{}"))
    row["events"] = json.loads(row.get("events", "[]"))

    return SpanResponse(
        trace_id=row["trace_id"],
        span_id=row["span_id"],
        parent_span_id=row.get("parent_span_id") or None,
        session_id=row.get("session_id") or None,
        name=row["name"],
        kind=row["kind"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        duration_ns=row.get("duration_ns", 0),
        status=row["status"],
        model=row.get("model") or None,
        input_tokens=row.get("input_tokens"),
        output_tokens=row.get("output_tokens"),
        cost_usd=row.get("cost_usd"),
        tool_name=row.get("tool_name") or None,
        attributes=row.get("attributes", {}),
        events=row.get("events", []),
        input=row.get("input") or None,
        output=row.get("output") or None,
        error=row.get("error") or None,
    )
