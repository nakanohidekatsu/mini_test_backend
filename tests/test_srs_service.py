import pytest
from datetime import timezone
from app.services.srs_service import calculate_next_review


def test_incorrect_answer_resets_streak():
    new_ease, new_streak, next_review = calculate_next_review(
        ease_factor=2.5, streak_correct=3, is_correct=False
    )
    assert new_streak == 0
    assert new_ease < 2.5
    assert new_ease >= 1.3


def test_correct_first_answer():
    new_ease, new_streak, next_review = calculate_next_review(
        ease_factor=2.5, streak_correct=0, is_correct=True
    )
    assert new_streak == 1
    diff = next_review - __import__('datetime').datetime.now(timezone.utc)
    assert 0 < diff.days <= 1


def test_ease_factor_minimum():
    _, _, _ = calculate_next_review(
        ease_factor=1.3, streak_correct=0, is_correct=False
    )
    new_ease, _, _ = calculate_next_review(
        ease_factor=1.3, streak_correct=0, is_correct=False
    )
    assert new_ease >= 1.3


def test_streak_increases_interval():
    _, _, review_1 = calculate_next_review(2.5, 1, True)
    _, _, review_6 = calculate_next_review(2.5, 2, True)
    now = __import__('datetime').datetime.now(timezone.utc)
    assert (review_6 - now).days > (review_1 - now).days
