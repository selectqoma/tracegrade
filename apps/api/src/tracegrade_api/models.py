import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    UUID,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="api_keys")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    trace_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    span_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(18, 8))
    total_tokens_in: Mapped[int | None] = mapped_column(BigInteger)
    total_tokens_out: Mapped[int | None] = mapped_column(BigInteger)
    has_error: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    summary: Mapped[str | None] = mapped_column(Text)
    summary_model: Mapped[str | None] = mapped_column(Text)
    user_metadata: Mapped[dict | None] = mapped_column(JSONB)


class Annotation(Base):
    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint("target_type IN ('span', 'trace', 'session')", name="ck_annotation_target_type"),
        CheckConstraint("author_kind IN ('human', 'llm_judge')", name="ck_annotation_author_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    author_kind: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[int | None] = mapped_column(SmallInteger)
    failure_modes: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    grader_type: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    source_annotation_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class EvalSuite(Base):
    __tablename__ = "eval_suites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class Eval(Base):
    __tablename__ = "evals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_suites.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    input_fixture: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    rubric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=False)
    expected: Mapped[dict | None] = mapped_column(JSONB)
    origin_trace_id: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_suites.id", ondelete="CASCADE"), nullable=False)
    agent_version: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    passed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    regressed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    report: Mapped[dict | None] = mapped_column(JSONB)
