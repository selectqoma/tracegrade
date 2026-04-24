import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings

logger = logging.getLogger(__name__)


async def run_eval_suite(ctx: dict, run_id: str, suite_id: str, agent_entrypoint: str | None = None) -> dict:
    """Execute all enabled evals in a suite and record results."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with async_session() as db:
            from sqlalchemy import text

            # Mark run as running
            await db.execute(
                text("UPDATE runs SET status = 'running', started_at = :now WHERE id = :rid"),
                {"rid": run_id, "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            # Load evals for this suite
            result = await db.execute(
                text("""
                    SELECT e.id, e.name, e.input_fixture, e.expected, r.grader_type, r.config as grader_config
                    FROM evals e
                    JOIN rubrics r ON e.rubric_id = r.id
                    WHERE e.suite_id = :sid AND e.enabled = true
                    ORDER BY e.created_at
                """),
                {"sid": suite_id},
            )
            evals = result.mappings().all()

            # Get previous run for regression detection
            prev_result = await db.execute(
                text("""
                    SELECT report FROM runs
                    WHERE suite_id = :sid AND status = 'completed' AND id != :rid
                    ORDER BY finished_at DESC LIMIT 1
                """),
                {"sid": suite_id, "rid": run_id},
            )
            prev_row = prev_result.mappings().first()
            prev_report = prev_row["report"] if prev_row and prev_row["report"] else {}
            prev_results = prev_report.get("eval_results", {})

            passed = 0
            failed = 0
            regressed = 0
            eval_results = {}

            for eval_row in evals:
                eval_id = str(eval_row["id"])
                eval_name = eval_row["name"]
                grader_type = eval_row["grader_type"]
                grader_config = eval_row["grader_config"] if isinstance(eval_row["grader_config"], dict) else json.loads(eval_row["grader_config"])
                input_fixture = eval_row["input_fixture"] if isinstance(eval_row["input_fixture"], dict) else json.loads(eval_row["input_fixture"])
                expected = eval_row["expected"]
                if expected and not isinstance(expected, dict):
                    expected = json.loads(expected)

                try:
                    # Run agent if entrypoint provided
                    output = {}
                    if agent_entrypoint:
                        output = await _run_agent(agent_entrypoint, input_fixture)

                    # Grade
                    grade_result = await _grade(grader_type, grader_config, output, expected)

                    eval_passed = grade_result["passed"]
                    if eval_passed:
                        passed += 1
                    else:
                        failed += 1

                    # Check for regression
                    was_passing = prev_results.get(eval_id, {}).get("passed", None)
                    is_regression = was_passing is True and not eval_passed
                    if is_regression:
                        regressed += 1

                    eval_results[eval_id] = {
                        "name": eval_name,
                        "passed": eval_passed,
                        "score": grade_result.get("score", 0),
                        "details": grade_result.get("details", ""),
                        "regression": is_regression,
                    }
                except Exception as e:
                    logger.exception("Failed to run eval %s", eval_name)
                    failed += 1
                    eval_results[eval_id] = {
                        "name": eval_name,
                        "passed": False,
                        "score": 0,
                        "details": f"Error: {e}",
                        "regression": False,
                    }

            report = {
                "passed": passed,
                "failed": failed,
                "regressed": regressed,
                "total": len(evals),
                "eval_results": eval_results,
            }

            await db.execute(
                text("""
                    UPDATE runs SET status = 'completed', finished_at = :now,
                    passed = :passed, failed = :failed, regressed = :regressed, report = :report
                    WHERE id = :rid
                """),
                {
                    "rid": run_id,
                    "now": datetime.now(timezone.utc),
                    "passed": passed,
                    "failed": failed,
                    "regressed": regressed,
                    "report": json.dumps(report),
                },
            )
            await db.commit()

            return report

    finally:
        await engine.dispose()


async def _run_agent(entrypoint: str, input_fixture: dict) -> dict:
    """Dynamically import and run the agent entrypoint."""
    import importlib

    module_path, func_name = entrypoint.rsplit(":", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return await func(input_fixture)
    return func(input_fixture)


async def _grade(grader_type: str, config: dict, output: dict, expected: dict | None) -> dict:
    """Run a grader and return {passed, score, details}."""
    if grader_type == "exact_match":
        fields = config.get("fields", [])
        all_match = True
        details = []
        for field in fields:
            actual = _get_nested(output, field)
            exp = _get_nested(expected or {}, field)
            if actual != exp:
                all_match = False
                details.append(f"{field}: expected {exp!r}, got {actual!r}")
        return {"passed": all_match, "score": 1.0 if all_match else 0.0, "details": "; ".join(details) or "All fields match"}

    elif grader_type == "tool_sequence":
        expected_seq = config.get("expected_sequence", [])
        actual_tools = output.get("tool_calls", [])
        allow_extras = config.get("allow_extras", True)

        actual_names = [t.get("tool_name", t.get("name", "")) for t in actual_tools]
        expected_names = [t["tool_name"] for t in expected_seq]

        if allow_extras:
            # Check subsequence
            j = 0
            for name in actual_names:
                if j < len(expected_names) and name == expected_names[j]:
                    j += 1
            match = j == len(expected_names)
        else:
            match = actual_names == expected_names

        return {"passed": match, "score": 1.0 if match else 0.0, "details": f"Expected: {expected_names}, Got: {actual_names}"}

    elif grader_type == "regex":
        import re
        pattern = config.get("pattern", "")
        field = config.get("field", "output")
        flags = config.get("flags", 0)
        text = str(_get_nested(output, field) or "")
        match = bool(re.search(pattern, text, flags=flags))
        return {"passed": match, "score": 1.0 if match else 0.0, "details": f"Pattern {'matched' if match else 'did not match'}: {pattern}"}

    elif grader_type == "llm_judge":
        import anthropic
        criteria = config.get("criteria", "Is the output correct?")
        model = config.get("model", settings.JUDGE_MODEL)

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system="You are an eval grader. Given an output and criteria, respond with JSON: {\"passed\": bool, \"score\": 0.0-1.0, \"details\": \"explanation\"}",
            messages=[{"role": "user", "content": f"Criteria: {criteria}\n\nOutput: {json.dumps(output)}\n\nExpected: {json.dumps(expected)}"}],
        )
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"passed": False, "score": 0.0, "details": "Failed to parse judge response"}

    elif grader_type == "groundedness":
        import anthropic
        context_field = config.get("context_field", "context")
        output_field = config.get("output_field", "output")
        model = config.get("model", settings.JUDGE_MODEL)

        context = str(_get_nested(output, context_field) or "")
        output_text = str(_get_nested(output, output_field) or "")

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system="Evaluate if the output is grounded in the provided context. Respond with JSON: {\"passed\": bool, \"score\": 0.0-1.0, \"details\": \"explanation\"}",
            messages=[{"role": "user", "content": f"Context: {context}\n\nOutput: {output_text}"}],
        )
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"passed": False, "score": 0.0, "details": "Failed to parse groundedness check"}

    return {"passed": False, "score": 0.0, "details": f"Unknown grader type: {grader_type}"}


def _get_nested(obj: dict, path: str):
    """Get a nested value from a dict using dot notation."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
