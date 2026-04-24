import json
import logging
import uuid

import anthropic
import clickhouse_connect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are an AI agent evaluation expert. Given a trace of an AI agent's execution and annotations marking where it failed, synthesize a regression test (eval) that would catch this failure mode in the future.

You must output valid JSON matching this schema:
{
    "name": "short descriptive name for the eval",
    "grader_type": "llm_judge" | "tool_sequence" | "exact_match" | "groundedness" | "regex",
    "grader_config": {
        // For llm_judge: {"criteria": "description of what to check", "model": "claude-haiku-4-5-20251001"}
        // For tool_sequence: {"expected_sequence": [{"tool_name": "...", "args_match": {...}}], "allow_extras": true}
        // For exact_match: {"fields": ["path.to.field"]}
        // For regex: {"pattern": "...", "field": "output"}
        // For groundedness: {"context_field": "context", "output_field": "output", "model": "claude-haiku-4-5-20251001"}
    },
    "input_fixture": {
        // The input that should be given to the agent to reproduce this scenario
    },
    "expected_behavior": "prose description of what the correct behavior should be",
    "rationale": "why this eval catches the specific failure mode annotated"
}

Focus on:
1. Making the eval specific enough to catch the exact failure mode
2. Making the input_fixture realistic and minimal
3. Choosing the right grader_type for the failure mode
4. Making the eval robust - it should pass on correct behavior and fail on the specific failure"""


async def synthesize_eval(ctx: dict, annotation_ids: list[str], project_id: str) -> dict:
    """Synthesize an eval from annotations and their origin traces."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    ch = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB,
    )

    try:
        async with async_session() as db:
            # Fetch annotations
            from sqlalchemy import text
            annotation_uuid_list = [uuid.UUID(a) for a in annotation_ids]
            result = await db.execute(
                text("SELECT * FROM annotations WHERE id = ANY(:ids)"),
                {"ids": annotation_uuid_list},
            )
            annotations = result.mappings().all()

            if not annotations:
                return {"error": "No annotations found"}

            # Fetch existing rubrics for dedup context
            result = await db.execute(
                text("SELECT name, grader_type, config FROM rubrics WHERE project_id = :pid LIMIT 20"),
                {"pid": project_id},
            )
            existing_rubrics = [dict(r) for r in result.mappings().all()]

        # Fetch origin traces from ClickHouse
        trace_ids = set()
        for ann in annotations:
            if ann["target_type"] == "trace":
                trace_ids.add(ann["target_id"])
            elif ann["target_type"] == "span":
                # Look up the trace for this span
                span_result = ch.query(
                    "SELECT trace_id FROM spans WHERE span_id = {sid:String} LIMIT 1",
                    parameters={"sid": ann["target_id"]},
                )
                for row in span_result.named_results():
                    trace_ids.add(row["trace_id"])

        trace_data = []
        for trace_id in trace_ids:
            rows = ch.query(
                "SELECT name, kind, status, model, tool_name, input, output, error, duration_ns "
                "FROM spans WHERE trace_id = {tid:String} ORDER BY start_time",
                parameters={"tid": trace_id},
            )
            spans = [dict(r) for r in rows.named_results()]
            trace_data.append({"trace_id": trace_id, "spans": spans})

        # Build prompt
        user_message = f"""## Annotations (marking what went wrong)
{json.dumps([dict(a) for a in annotations], indent=2, default=str)}

## Origin Traces
{json.dumps(trace_data, indent=2, default=str)}

## Existing Rubrics (do not duplicate these)
{json.dumps(existing_rubrics, indent=2, default=str)}

Synthesize a regression eval that catches this failure mode."""

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.SYNTHESIS_MODEL,
            max_tokens=4096,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse JSON from response
        text_content = response.content[0].text
        # Try to extract JSON
        start = text_content.find("{")
        end = text_content.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text_content[start:end])
            return {"status": "draft", "eval_draft": result}

        return {"status": "error", "error": "Failed to parse synthesis output", "raw": text_content}

    finally:
        ch.close()
        await engine.dispose()
