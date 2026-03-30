import pytest
from pydantic import ValidationError
from app.schemas.question import GeneratedQuestion, LLMGenerateResponse


def test_valid_question():
    q = GeneratedQuestion(
        question_text="問題文",
        choices=["A", "B", "C", "D"],
        correct_index=0,
        explanation="解説",
        category="テスト",
        difficulty="easy",
        tags=["tag1"],
    )
    assert q.correct_index == 0
    assert len(q.choices) == 4


def test_invalid_correct_index_raises():
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question_text="問題文",
            choices=["A", "B", "C", "D"],
            correct_index=99,
            explanation="解説",
            category="テスト",
            difficulty="easy",
        )


def test_llm_response_parses_multiple():
    data = {
        "questions": [
            {
                "question_text": "Q1",
                "choices": ["A", "B", "C", "D"],
                "correct_index": 1,
                "explanation": "解説1",
                "category": "C1",
                "difficulty": "medium",
            },
            {
                "question_text": "Q2",
                "choices": ["X", "Y"],
                "correct_index": 0,
                "explanation": "解説2",
                "category": "C2",
                "difficulty": "hard",
            },
        ]
    }
    resp = LLMGenerateResponse(**data)
    assert len(resp.questions) == 2
    assert resp.questions[0].difficulty.value == "medium"


def test_invalid_difficulty_raises():
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question_text="Q",
            choices=["A", "B"],
            correct_index=0,
            explanation="解説",
            category="C",
            difficulty="unknown",
        )
