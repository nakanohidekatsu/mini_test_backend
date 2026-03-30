from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class ChoiceSchema(BaseModel):
    id: str
    choice_text: str
    display_order: int


class QuestionSchema(BaseModel):
    id: str
    user_id: str
    source_id: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    question_text: str
    explanation: Optional[str] = None
    correct_choice_id: Optional[str] = None
    created_at: str
    choices: list[ChoiceSchema] = []
    tags: list[str] = []


class GeneratedChoice(BaseModel):
    choice_text: str
    display_order: int


class GeneratedQuestion(BaseModel):
    question_text: str
    choices: list[str]
    correct_index: int
    explanation: str
    category: str
    difficulty: Difficulty
    tags: list[str] = []

    @field_validator("correct_index")
    @classmethod
    def validate_correct_index(cls, v: int, info) -> int:
        choices = info.data.get("choices", [])
        if not 0 <= v < len(choices):
            raise ValueError(f"correct_index {v} is out of range")
        return v


class LLMGenerateResponse(BaseModel):
    questions: list[GeneratedQuestion]
