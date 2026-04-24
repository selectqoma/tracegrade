from abc import ABC, abstractmethod

from pydantic import BaseModel


class GraderResult(BaseModel):
    passed: bool
    score: float  # 0.0 - 1.0
    details: str
    metadata: dict = {}


class BaseGrader(ABC):
    @abstractmethod
    async def grade(self, output: dict, expected: dict | None, config: dict) -> GraderResult:
        ...
