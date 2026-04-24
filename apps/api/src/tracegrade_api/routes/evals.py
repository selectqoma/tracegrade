import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_project
from ..db import get_db, get_redis
from ..models import Eval, EvalSuite, Rubric, Run
from ..schemas import (
    EvalCreate,
    EvalResponse,
    RubricCreate,
    RubricResponse,
    RubricSynthesizeRequest,
    RunCreate,
    RunReportResponse,
    RunResponse,
)

router = APIRouter(prefix="/api", tags=["evals"])


# --- Rubrics ---

@router.post("/rubrics/synthesize", status_code=202)
async def synthesize_rubric(
    body: RubricSynthesizeRequest,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    redis = await get_redis()
    job_id = str(uuid.uuid4())
    # Enqueue job for worker
    await redis.rpush(
        "arq:queue",
        f'{{"function":"synthesize_eval","args":[{[str(a) for a in body.annotation_ids]},"{project_id}"],"job_id":"{job_id}"}}',
    )
    return {"job_id": job_id, "status": "queued"}


@router.post("/rubrics", response_model=RubricResponse, status_code=201)
async def create_rubric(
    body: RubricCreate,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rubric = Rubric(
        project_id=body.project_id,
        name=body.name,
        grader_type=body.grader_type,
        config=body.config,
        source_annotation_ids=body.source_annotation_ids,
        created_by=body.created_by,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return RubricResponse.model_validate(rubric)


@router.get("/rubrics/{rubric_id}", response_model=RubricResponse)
async def get_rubric(
    rubric_id: uuid.UUID,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Rubric).where(Rubric.id == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return RubricResponse.model_validate(rubric)


# --- Evals ---

@router.post("/evals", response_model=EvalResponse, status_code=201)
async def create_eval(
    body: EvalCreate,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    eval_obj = Eval(
        suite_id=body.suite_id,
        name=body.name,
        input_fixture=body.input_fixture,
        rubric_id=body.rubric_id,
        expected=body.expected,
        origin_trace_id=body.origin_trace_id,
        version=body.version,
        enabled=body.enabled,
    )
    db.add(eval_obj)
    await db.commit()
    await db.refresh(eval_obj)
    return EvalResponse.model_validate(eval_obj)


@router.get("/evals", response_model=list[EvalResponse])
async def list_evals(
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
    suite_id: uuid.UUID | None = Query(None),
):
    stmt = select(Eval)
    if suite_id:
        stmt = stmt.where(Eval.suite_id == suite_id)
    result = await db.execute(stmt.order_by(Eval.created_at.desc()))
    evals = result.scalars().all()
    return [EvalResponse.model_validate(e) for e in evals]


# --- Runs ---

@router.post("/suites/{suite_id}/run", response_model=RunResponse, status_code=202)
async def start_run(
    suite_id: uuid.UUID,
    body: RunCreate,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Verify suite exists
    result = await db.execute(select(EvalSuite).where(EvalSuite.id == suite_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Suite not found")

    run = Run(
        suite_id=suite_id,
        agent_version=body.agent_version,
        triggered_by=body.triggered_by or "manual",
        status="pending",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue for worker
    redis = await get_redis()
    await redis.rpush(
        "arq:queue",
        f'{{"function":"run_eval_suite","args":["{run.id}","{suite_id}"],"job_id":"{run.id}"}}',
    )

    return RunResponse.model_validate(run)


@router.get("/runs/{run_id}", response_model=RunReportResponse)
async def get_run(
    run_id: uuid.UUID,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunReportResponse.model_validate(run)
