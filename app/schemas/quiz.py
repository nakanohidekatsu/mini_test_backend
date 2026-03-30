from pydantic import BaseModel
from typing import Optional
from enum import Enum


class QuizMode(str, Enum):
    random = "random"
    category = "category"
    srs = "srs"
    weak = "weak"


class QuizStartRequest(BaseModel):
    mode: QuizMode
    category: Optional[str] = None
    limit: int = 10


class QuizAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    selected_choice_id: Optional[str] = None
    elapsed_seconds: int = 0


class QuizAnswerResponse(BaseModel):
    is_correct: bool
    correct_choice_id: str
    explanation: Optional[str]
    next_review_at: Optional[str]
