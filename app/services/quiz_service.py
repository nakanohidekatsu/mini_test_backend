from supabase import create_client, Client
from app.core.config import settings
from app.schemas.quiz import QuizStartRequest, QuizAnswerRequest, QuizAnswerResponse
from app.services.srs_service import calculate_next_review
from fastapi import HTTPException
from datetime import datetime, timezone
import random
import structlog

logger = structlog.get_logger()


class QuizService:
    def __init__(self, user_token: str):
        self.db: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self.db.postgrest.auth(user_token)

    async def start_session(self, user_id: str, req: QuizStartRequest) -> dict:
        query = self.db.from_("questions").select(
            "id, question_text, question_choices!question_choices_question_id_fkey(*)"
        )

        if req.mode == "question_set" and req.question_set_id:
            query = query.eq("question_set_id", req.question_set_id)
        elif req.category:
            query = query.eq("category", req.category)
        if req.mode == "srs":
            now = datetime.now(timezone.utc).isoformat()
            progress_result = self.db.from_("user_progress").select("question_id").eq(
                "user_id", user_id
            ).lte("next_review_at", now).limit(req.limit).execute()
            ids = [r["question_id"] for r in progress_result.data]
            if ids:
                query = query.in_("id", ids)

        # 問題集・ランダムモードは全件取得してシャッフル
        if req.mode in ("question_set", "random"):
            result = query.execute()
            questions = result.data
            random.shuffle(questions)
            questions = questions[:req.limit]
        else:
            result = query.limit(req.limit).execute()
            questions = result.data
        if not questions:
            raise HTTPException(status_code=404, detail="No questions found")

        session_result = self.db.from_("quiz_sessions").insert({
            "user_id": user_id,
            "mode": req.mode,
            "category": req.category,
            "total_questions": len(questions),
        }).execute()

        session_id = session_result.data[0]["id"]
        return {"session_id": session_id, "questions": questions}

    async def submit_answer(self, user_id: str, req: QuizAnswerRequest) -> QuizAnswerResponse:
        q_result = self.db.from_("questions").select(
            "correct_choice_id, explanation"
        ).eq("id", req.question_id).eq("user_id", user_id).single().execute()

        if not q_result.data:
            raise HTTPException(status_code=404, detail="Question not found")

        q = q_result.data
        is_correct = req.selected_choice_id == q["correct_choice_id"]

        # Save answer
        self.db.from_("quiz_session_answers").insert({
            "session_id": req.session_id,
            "question_id": req.question_id,
            "selected_choice_id": req.selected_choice_id,
            "is_correct": is_correct,
            "elapsed_seconds": req.elapsed_seconds,
        }).execute()

        # Update SRS progress
        progress_result = self.db.from_("user_progress").select("*").eq(
            "user_id", user_id
        ).eq("question_id", req.question_id).execute()

        next_review = None
        if progress_result.data:
            p = progress_result.data[0]
            new_ease, new_streak, next_review = calculate_next_review(
                ease_factor=p["ease_factor"],
                streak_correct=p["streak_correct"],
                is_correct=is_correct,
            )
            self.db.from_("user_progress").update({
                "total_attempts": p["total_attempts"] + 1,
                "correct_attempts": p["correct_attempts"] + (1 if is_correct else 0),
                "streak_correct": new_streak,
                "ease_factor": new_ease,
                "last_answered_at": datetime.now(timezone.utc).isoformat(),
                "next_review_at": next_review.isoformat(),
            }).eq("id", p["id"]).execute()
        else:
            _, new_streak, next_review = calculate_next_review(2.5, 0, is_correct)
            self.db.from_("user_progress").insert({
                "user_id": user_id,
                "question_id": req.question_id,
                "total_attempts": 1,
                "correct_attempts": 1 if is_correct else 0,
                "streak_correct": new_streak,
                "last_answered_at": datetime.now(timezone.utc).isoformat(),
                "next_review_at": next_review.isoformat(),
            }).execute()

        return QuizAnswerResponse(
            is_correct=is_correct,
            correct_choice_id=q["correct_choice_id"],
            explanation=q.get("explanation"),
            next_review_at=next_review.isoformat() if next_review else None,
        )

    async def finish_session(self, user_id: str, session_id: str) -> dict:
        answers_result = self.db.from_("quiz_session_answers").select("is_correct, elapsed_seconds").eq(
            "session_id", session_id
        ).execute()
        answers = answers_result.data
        score = sum(1 for a in answers if a["is_correct"])
        total_seconds = sum((a.get("elapsed_seconds") or 0) for a in answers)

        self.db.from_("quiz_sessions").update({
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "score": score,
        }).eq("id", session_id).eq("user_id", user_id).execute()

        # study_logs を当日分 upsert（questions_answered / total_seconds を加算）
        today = datetime.now(timezone.utc).date().isoformat()
        existing = self.db.from_("study_logs").select("*").eq("user_id", user_id).eq("study_date", today).execute()
        if existing.data:
            log = existing.data[0]
            self.db.from_("study_logs").update({
                "questions_answered": log["questions_answered"] + len(answers),
                "total_seconds": log["total_seconds"] + total_seconds,
            }).eq("id", log["id"]).execute()
        else:
            self.db.from_("study_logs").insert({
                "user_id": user_id,
                "study_date": today,
                "questions_answered": len(answers),
                "total_seconds": total_seconds,
            }).execute()

        return {"session_id": session_id, "score": score, "total": len(answers)}
