from datetime import datetime, timezone, timedelta


def calculate_next_review(
    ease_factor: float,
    streak_correct: int,
    is_correct: bool,
) -> tuple[float, int, datetime]:
    """SM-2アルゴリズムベースのSRS計算"""
    if not is_correct:
        new_ease = max(1.3, ease_factor - 0.2)
        new_streak = 0
        interval_days = 1
    else:
        new_streak = streak_correct + 1
        if new_streak == 1:
            interval_days = 1
        elif new_streak == 2:
            interval_days = 6
        else:
            interval_days = round((new_streak - 1) * ease_factor)
        new_ease = ease_factor + (0.1 - (5 - 4) * (0.08 + (5 - 4) * 0.02))
        new_ease = max(1.3, new_ease)

    next_review = datetime.now(timezone.utc) + timedelta(days=interval_days)
    return new_ease, new_streak, next_review
