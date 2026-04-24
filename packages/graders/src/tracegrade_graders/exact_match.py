from .base import BaseGrader, GraderResult


def _get_nested(obj: dict, path: str):
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


class ExactMatchGrader(BaseGrader):
    async def grade(self, output: dict, expected: dict | None, config: dict) -> GraderResult:
        fields = config.get("fields", [])
        mismatches = []

        for field in fields:
            actual = _get_nested(output, field)
            exp = _get_nested(expected or {}, field)
            if actual != exp:
                mismatches.append(f"{field}: expected {exp!r}, got {actual!r}")

        passed = len(mismatches) == 0
        return GraderResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            details="; ".join(mismatches) if mismatches else "All fields match",
        )
