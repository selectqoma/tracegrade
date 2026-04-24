import json
import os

import anthropic

from .base import BaseGrader, GraderResult


class GroundednessGrader(BaseGrader):
    async def grade(self, output: dict, expected: dict | None, config: dict) -> GraderResult:
        context_field = config.get("context_field", "context")
        output_field = config.get("output_field", "output")
        model = config.get("model", "claude-haiku-4-5-20251001")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        # Extract fields
        context = output
        for part in context_field.split("."):
            context = context.get(part, "") if isinstance(context, dict) else ""

        output_text = output
        for part in output_field.split("."):
            output_text = output_text.get(part, "") if isinstance(output_text, dict) else ""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=(
                "Evaluate if the output is fully grounded in (supported by) the provided context. "
                "Check for hallucinations or claims not supported by the context. "
                "Respond with JSON only: {\"passed\": bool, \"score\": float 0-1, \"details\": \"explanation\"}"
            ),
            messages=[{
                "role": "user",
                "content": f"Context:\n{context}\n\nOutput to evaluate:\n{output_text}",
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

        return GraderResult(passed=False, score=0.0, details="Failed to parse groundedness response")
