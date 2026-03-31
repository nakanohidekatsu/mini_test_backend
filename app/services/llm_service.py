import json
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from supabase import create_client, Client
import anthropic
from app.core.config import settings
from app.schemas.question import LLMGenerateResponse, GeneratedQuestion
from fastapi import HTTPException

logger = structlog.get_logger()

GENERATE_PROMPT = """以下のテキストから選択問題を{max_questions}問生成してください。

テキスト:
{text}

以下のJSONスキーマで厳密に出力してください。JSONのみ出力し、説明文は不要です。
{{
  "questions": [
    {{
      "question_text": "問題文",
      "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
      "correct_index": 0,
      "explanation": "解説文",
      "category": "カテゴリ",
      "difficulty": "easy|medium|hard",
      "tags": ["タグ1", "タグ2"]
    }}
  ]
}}

品質要件:
- 正確な問題のみ生成する
- 正解が1つになるよう選択肢を設計する
- 学習に役立つ詳細な解説を付ける
- 元テキストに忠実な内容にする"""


class LLMService:
    def __init__(self, user_token: str):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.db: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self.db.postgrest.auth(user_token)

    async def generate_questions(self, user_id: str, source_ids: list[str], max_questions: int = 10, question_set_id: str = None) -> dict:
        texts = []
        for source_id in source_ids:
            source_result = self.db.from_("question_sources").select("*").eq("id", source_id).eq("user_id", user_id).single().execute()
            if not source_result.data:
                logger.warning("source_not_found", source_id=source_id)
                continue
            raw_text = (source_result.data.get("raw_text", "") or "").strip()
            if raw_text:
                name = source_result.data.get("source_name", "")
                texts.append(f"=== {name} ===\n{raw_text}")

        if not texts:
            raise HTTPException(status_code=422, detail="PDFからテキストを抽出できませんでした。")

        combined_text = "\n\n".join(texts)
        questions = await self._call_llm(raw_text=combined_text, max_questions=max_questions)
        saved = await self._save_questions(user_id=user_id, source_id=source_ids[0], questions=questions, question_set_id=question_set_id)
        return {"generated": len(saved), "questions": saved}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_llm(self, raw_text: str, max_questions: int) -> list[GeneratedQuestion]:
        prompt = GENERATE_PROMPT.format(text=raw_text[:6000], max_questions=max_questions)
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()
            # マークダウンコードブロックを除去
            if content.startswith("```"):
                lines = content.splitlines()
                inner = [l for l in lines[1:] if l.strip() != "```"]
                content = "\n".join(inner)
            # { ... } の範囲を抽出して不要なテキストを除去
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1:
                logger.error("llm_no_json_found", content_preview=content[:200])
                raise json.JSONDecodeError("no JSON object found", content, 0)
            content = content[start:end + 1]
            if not content:
                logger.error("llm_empty_response")
                raise json.JSONDecodeError("empty response", "", 0)
            data = json.loads(content)
            validated = LLMGenerateResponse(**data)
            return validated.questions
        except json.JSONDecodeError as e:
            logger.error("llm_json_decode_error", error=str(e))
            raise
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            raise

    async def _save_questions(self, user_id: str, source_id: str, questions: list[GeneratedQuestion], question_set_id: str = None) -> list:
        saved = []
        for q in questions:
            import hashlib
            dup_hash = hashlib.sha256(q.question_text.encode()).hexdigest()

            existing = self.db.from_("questions").select("id").eq("duplicate_hash", dup_hash).eq("user_id", user_id).execute()
            if existing.data:
                logger.info("duplicate_question_skipped", hash=dup_hash)
                continue

            insert_data = {
                "user_id": user_id,
                "source_id": source_id,
                "question_text": q.question_text,
                "explanation": q.explanation,
                "category": q.category,
                "difficulty": q.difficulty.value,
                "duplicate_hash": dup_hash,
            }
            if question_set_id:
                insert_data["question_set_id"] = question_set_id
            q_result = self.db.from_("questions").insert(insert_data).execute()
            q_id = q_result.data[0]["id"]

            choices = [
                {"question_id": q_id, "choice_text": c, "display_order": i}
                for i, c in enumerate(q.choices)
            ]
            choice_result = self.db.from_("question_choices").insert(choices).execute()
            correct_choice_id = choice_result.data[q.correct_index]["id"]

            self.db.from_("questions").update({"correct_choice_id": correct_choice_id}).eq("id", q_id).execute()

            if q.tags:
                tags = [{"question_id": q_id, "tag": t} for t in q.tags]
                self.db.from_("question_tags").insert(tags).execute()

            saved.append({"id": q_id, "question_text": q.question_text})
        return saved
