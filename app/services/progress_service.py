from supabase import create_client, Client
from app.core.config import settings
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


class ProgressService:
    def __init__(self, user_token: str):
        self.db: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self.db.postgrest.auth(user_token)

    async def get_dashboard(self, user_id: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).date().isoformat()

        total_q = self.db.from_("questions").select("*", count="exact", head=True).eq("user_id", user_id).execute()
        review_due = self.db.from_("user_progress").select("*", count="exact", head=True).eq("user_id", user_id).lte("next_review_at", now).execute()
        today_log = self.db.from_("study_logs").select("*").eq("user_id", user_id).eq("study_date", today).execute()

        return {
            "total_questions": total_q.count or 0,
            "review_due_count": review_due.count or 0,
            "today_questions_answered": today_log.data[0]["questions_answered"] if today_log.data else 0,
            "today_total_seconds": today_log.data[0]["total_seconds"] if today_log.data else 0,
        }

    async def get_stats(self, user_id: str) -> dict:
        progress = self.db.from_("user_progress").select("*").eq("user_id", user_id).execute()
        data = progress.data
        total = len(data)
        correct = sum(p["correct_attempts"] for p in data)
        total_attempts = sum(p["total_attempts"] for p in data)
        accuracy = round(correct / total_attempts * 100, 1) if total_attempts > 0 else 0
        mastered = sum(1 for p in data if p["mastery_level"] >= 3)
        return {"total": total, "accuracy_rate": accuracy, "mastered": mastered}

    async def get_history(self, user_id: str) -> list:
        result = self.db.from_("study_logs").select("*").eq("user_id", user_id).order("study_date", desc=True).limit(30).execute()
        return result.data
