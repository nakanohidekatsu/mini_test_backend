from supabase import create_client, Client
from app.core.config import settings
from fastapi import UploadFile, HTTPException
import json
import csv
import io
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger()


class QuestionService:
    def __init__(self, user_token: str):
        self.db: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self.db.postgrest.auth(user_token)

    async def list_questions(self, user_id: str, **filters) -> dict:
        query = self.db.from_("questions").select(
            "*, question_choices!question_choices_question_id_fkey(*), question_tags(tag)"
        ).eq("user_id", user_id)

        if filters.get("question_set_id"):
            query = query.eq("question_set_id", filters["question_set_id"])
        if filters.get("category"):
            query = query.eq("category", filters["category"])
        if filters.get("difficulty"):
            query = query.eq("difficulty", filters["difficulty"])
        if filters.get("keyword"):
            query = query.ilike("question_text", f"%{filters['keyword']}%")

        page = filters.get("page", 1)
        per_page = filters.get("per_page", 20)
        query = query.range((page - 1) * per_page, page * per_page - 1)

        result = query.execute()
        return {"questions": result.data, "page": page, "per_page": per_page}

    async def get_question(self, user_id: str, question_id: str) -> dict:
        result = self.db.from_("questions").select(
            "*, question_choices!question_choices_question_id_fkey(*), question_tags(tag)"
        ).eq("id", question_id).eq("user_id", user_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        return result.data

    async def update_question(self, user_id: str, question_id: str, data: dict) -> dict:
        # Update question fields
        question_fields = {k: v for k, v in data.items() if k in (
            "question_text", "explanation", "category", "difficulty", "question_set_id", "correct_choice_id"
        )}
        result = self.db.from_("questions").update(question_fields).eq("id", question_id).eq("user_id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")

        # Update choice texts
        for choice in data.get("choices", []):
            self.db.from_("question_choices").update({"choice_text": choice["choice_text"]}).eq("id", choice["id"]).execute()

        return await self.get_question(user_id, question_id)

    async def update_question_set(self, user_id: str, question_id: str, question_set_id: str | None) -> dict:
        result = self.db.from_("questions").update({
            "question_set_id": question_set_id,
        }).eq("id", question_id).eq("user_id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        return result.data[0]

    async def delete_question(self, user_id: str, question_id: str) -> dict:
        result = self.db.from_("questions").delete().eq("id", question_id).eq("user_id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Question not found")
        return {"deleted": True}

    async def get_review_questions(self, user_id: str, limit: int) -> list:
        now = datetime.now(timezone.utc).isoformat()
        result = self.db.from_("user_progress").select(
            "question_id, questions(*, question_choices!question_choices_question_id_fkey(*))"
        ).eq("user_id", user_id).lte("next_review_at", now).limit(limit).execute()
        return result.data

    async def import_csv(self, user_id: str, file: UploadFile) -> dict:
        content = await file.read()
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        count = 0
        errors = []
        for i, row in enumerate(reader):
            try:
                await self._save_question_row(user_id, row)
                count += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)})
        return {"imported": count, "errors": errors}

    async def import_json(self, user_id: str, file: UploadFile) -> dict:
        content = await file.read()
        data = json.loads(content)
        questions = data if isinstance(data, list) else data.get("questions", [])
        count = 0
        errors = []
        for i, row in enumerate(questions):
            try:
                await self._save_question_row(user_id, row)
                count += 1
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        return {"imported": count, "errors": errors}

    async def _save_question_row(self, user_id: str, row: dict) -> None:
        q_result = self.db.from_("questions").insert({
            "user_id": user_id,
            "question_text": row["question_text"],
            "explanation": row.get("explanation"),
            "category": row.get("category"),
            "difficulty": row.get("difficulty"),
        }).execute()
        q_id = q_result.data[0]["id"]

        choices_raw = row.get("choices", [])
        if isinstance(choices_raw, str):
            choices_raw = json.loads(choices_raw)

        choices = []
        for i, c in enumerate(choices_raw):
            choices.append({"question_id": q_id, "choice_text": c, "display_order": i})
        if choices:
            choice_result = self.db.from_("question_choices").insert(choices).execute()
            correct_idx = int(row.get("correct_index", 0))
            correct_choice_id = choice_result.data[correct_idx]["id"]
            self.db.from_("questions").update({"correct_choice_id": correct_choice_id}).eq("id", q_id).execute()

    async def export_csv(self, user_id: str) -> str:
        result = self.db.from_("questions").select(
            "*, question_choices!question_choices_question_id_fkey(*), question_tags(tag)"
        ).eq("user_id", user_id).execute()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "question_text", "explanation", "category", "difficulty", "choices", "correct_index", "tags"])
        for q in result.data:
            choices = sorted(q.get("question_choices", []), key=lambda c: c["display_order"])
            correct_idx = next((i for i, c in enumerate(choices) if c["id"] == q.get("correct_choice_id")), 0)
            writer.writerow([
                q["id"], q["question_text"], q.get("explanation", ""),
                q.get("category", ""), q.get("difficulty", ""),
                json.dumps([c["choice_text"] for c in choices], ensure_ascii=False),
                correct_idx,
                json.dumps([t["tag"] for t in q.get("question_tags", [])], ensure_ascii=False),
            ])
        return output.getvalue()

    async def export_json(self, user_id: str) -> dict:
        result = self.db.from_("questions").select(
            "*, question_choices!question_choices_question_id_fkey(*), question_tags(tag)"
        ).eq("user_id", user_id).execute()
        return {"questions": result.data}
