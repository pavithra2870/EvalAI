from typing import List

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The exam question")
    answer: str = Field(..., min_length=1, description="The student's answer")


class Criterion(BaseModel):
    name: str
    description: str
    marks_weight: int


class Rubric(BaseModel):
    id: str
    subject: str
    topic: str
    max_marks: int
    criteria: List[Criterion]


class EvaluateResponse(BaseModel):
    rubric: Rubric
    marks_awarded: int
    max_marks: int
    feedback: str
    justification: str
    rubric_id: str
