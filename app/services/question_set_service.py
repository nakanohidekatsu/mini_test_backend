from supabase import create_client, Client
from app.core.config import settings
from fastapi import HTTPException
import structlog

logger = structlog.get_logger()


class QuestionSetService:
    def __init__(self, user_token: str):
        self.db: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self.db.postgrest.auth(user_token)

    async def list_sets(self, user_id: str) -> list:
        result = self.db.from_("question_sets").select("*").order("created_at", desc=True).execute()
        sets = result.data
        for s in sets:
            count_result = self.db.from_("questions").select("id").eq("question_set_id", s["id"]).execute()
            s["question_count"] = len(count_result.data)
        return sets

    async def create_set(self, user_id: str, name: str, description: str = "") -> dict:
        result = self.db.from_("question_sets").insert({
            "user_id": user_id,
            "name": name,
            "description": description,
        }).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create question set")
        s = result.data[0]
        s["question_count"] = 0
        return s

    async def update_set(self, user_id: str, set_id: str, name: str, description: str = "") -> dict:
        result = self.db.from_("question_sets").update({
            "name": name,
            "description": description,
        }).eq("id", set_id).eq("user_id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question set not found")
        s = result.data[0]
        count_result = self.db.from_("questions").select("id").eq("question_set_id", set_id).execute()
        s["question_count"] = len(count_result.data)
        return s

    async def delete_set(self, user_id: str, set_id: str) -> dict:
        result = self.db.from_("question_sets").delete().eq("id", set_id).eq("user_id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question set not found")
        return {"deleted": True}
