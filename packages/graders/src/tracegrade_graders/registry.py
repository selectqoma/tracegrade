from .base import BaseGrader
from .exact_match import ExactMatchGrader
from .groundedness import GroundednessGrader
from .llm_judge import LLMJudgeGrader
from .regex import RegexGrader
from .tool_sequence import ToolSequenceGrader

GRADER_REGISTRY: dict[str, type[BaseGrader]] = {
    "llm_judge": LLMJudgeGrader,
    "exact_match": ExactMatchGrader,
    "tool_sequence": ToolSequenceGrader,
    "regex": RegexGrader,
    "groundedness": GroundednessGrader,
}


def get_grader(grader_type: str) -> BaseGrader:
    cls = GRADER_REGISTRY.get(grader_type)
    if not cls:
        raise ValueError(f"Unknown grader type: {grader_type}. Available: {list(GRADER_REGISTRY.keys())}")
    return cls()
