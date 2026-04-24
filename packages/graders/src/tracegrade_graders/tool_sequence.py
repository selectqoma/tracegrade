from .base import BaseGrader, GraderResult


class ToolSequenceGrader(BaseGrader):
    async def grade(self, output: dict, expected: dict | None, config: dict) -> GraderResult:
        expected_seq = config.get("expected_sequence", [])
        actual_tools = output.get("tool_calls", [])
        allow_extras = config.get("allow_extras", True)

        actual_names = [t.get("tool_name", t.get("name", "")) for t in actual_tools]
        expected_names = [t["tool_name"] for t in expected_seq]

        if allow_extras:
            j = 0
            for name in actual_names:
                if j < len(expected_names) and name == expected_names[j]:
                    j += 1
            passed = j == len(expected_names)
        else:
            passed = actual_names == expected_names

        return GraderResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            details=f"Expected: {expected_names}, Got: {actual_names}",
        )
