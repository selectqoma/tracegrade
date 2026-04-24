import json
import os

import anthropic

from .base import BaseGrader, GraderResult


class LLMJudgeGrader(BaseGrader):
    async def grade(self, output: dict, expected: dict | None, config: dict) -> GraderResult:
        criteria = config.get("criteria", "Is the output correct and complete?")
        model = config.get("model", "claude-haiku-4-5-20251001")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=(
                "You are an eval grader. Evaluate the output against the criteria. "
                "Respond with JSON only: {\"passed\": bool, \"score\": float 0-1, \"details\": \"explanation\"}"
            ),
            messages=[{
                "role": "user",
                "content": f"Criteria: {criteria}\n\nOutput:\n{json.dumps(output, indent=2)}\n\nExpected:\n{json.dumps(expected, indent=2) if expected else 'N/A'}",
            }],
        )

        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end])
            return GraderResult(
                passed=parsed.get("passed", False),
                score=parsed.get("score", 0.0),
                details=parsed.get("details", ""),
            )

        return GraderResult(passed=False, score=0.0, details="Failed to parse LLM judge response")
