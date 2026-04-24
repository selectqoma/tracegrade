"""SpanBuffer: accumulates spans in memory and flushes to ClickHouse."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SPAN_COLUMNS = [
    "trace_id",
    "span_id",
    "parent_span_id",
    "session_id",
    "name",
    "kind",
    "start_time",
    "end_time",
    "duration_ns",
    "status",
    "model",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "tool_name",
    "attributes",
    "events",
    "input",
    "output",
    "error",
]


@dataclass
class NormalizedSpan:
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
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    input: str | None = None
    output: str | None = None
    error: str | None = None

    def to_row(self) -> list[Any]:
        return [
            self.trace_id,
            self.span_id,
            self.parent_span_id or "",
            self.session_id or "",
            self.name,
            self.kind,
            self.start_time,
            self.end_time,
            self.duration_ns,
            self.status,
            self.model or "",
            self.input_tokens or 0,
            self.output_tokens or 0,
            self.cost_usd or 0.0,
            self.tool_name or "",
            json.dumps(self.attributes),
            json.dumps(self.events),
            self.input or "",
            self.output or "",
            self.error or "",
        ]


class SpanBuffer:
    def __init__(
        self,
        clickhouse_client: Any,
        table: str = "spans",
        batch_size: int = 1000,
        flush_interval: float = 5.0,
    ) -> None:
        self._client = clickhouse_client
        self._table = table
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: list[NormalizedSpan] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None

    def start(self) -> None:
        self._flush_task = asyncio.create_task(self._background_flush())

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    async def add(self, span: NormalizedSpan) -> None:
        async with self._lock:
            self._buffer.append(span)
            if len(self._buffer) >= self._batch_size:
                await self._flush_locked()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        try:
            rows = [span.to_row() for span in batch]
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.insert(self._table, rows, column_names=SPAN_COLUMNS),
            )
            logger.debug("Flushed %d spans to ClickHouse", len(rows))
        except Exception:
            logger.exception("Failed to flush %d spans to ClickHouse", len(batch))
            # Re-queue spans to avoid loss on transient errors
            self._buffer = batch + self._buffer

    async def _background_flush(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            try:
                await self.flush()
            except Exception:
                logger.exception("Background flush error")
