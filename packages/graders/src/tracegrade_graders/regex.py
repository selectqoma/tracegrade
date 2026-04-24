import re

from .base import BaseGrader, GraderResult


class RegexGrader(BaseGrader):
    async def grade(self, output: dict, expected: dict | None, config: dict) -> GraderResult:
        pattern = config.get("pattern", "")
        field = config.get("field", "output")
        flags = config.get("flags", 0)

        # Navigate to field
        value = output
        for part in field.split("."):
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                value = ""
                break

        text = str(value)
        matched = bool(re.search(pattern, text, flags=flags))

        return GraderResult(
            passed=matched,
            score=1.0 if matched else 0.0,
            details=f"Pattern {'matched' if matched else 'did not match'}: {pattern}",
        )
