import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_project
from ..db import get_db
from ..models import Annotation
from ..schemas import AnnotationCreate, AnnotationResponse

router = APIRouter(prefix="/api", tags=["annotations"])


@router.post("/annotations", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    body: AnnotationCreate,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    annotation = Annotation(
        target_type=body.target_type,
        target_id=body.target_id,
        author_id=body.author_id,
        author_kind=body.author_kind,
        verdict=body.verdict,
        failure_modes=body.failure_modes,
        note=body.note,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return AnnotationResponse.model_validate(annotation)


@router.get("/annotations", response_model=list[AnnotationResponse])
async def list_annotations(
    target: str = Query(..., description="Format: type:id, e.g. span:abc123"),
    project_id: Annotated[uuid.UUID, Depends(require_project)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    parts = target.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="target must be in format type:id")

    target_type, target_id = parts
    result = await db.execute(
        select(Annotation)
        .where(Annotation.target_type == target_type, Annotation.target_id == target_id)
        .order_by(Annotation.created_at.desc())
    )
    annotations = result.scalars().all()
    return [AnnotationResponse.model_validate(a) for a in annotations]


@router.delete("/annotations/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: uuid.UUID,
    project_id: Annotated[uuid.UUID, Depends(require_project)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    await db.execute(delete(Annotation).where(Annotation.id == annotation_id))
    await db.commit()
