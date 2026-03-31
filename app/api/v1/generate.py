from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.auth import get_current_user, CurrentUser
from app.services.llm_service import LLMService

router = APIRouter()


class GenerateRequest(BaseModel):
    source_ids: list[str]
    max_questions: int = 10
    question_set_id: str | None = None


@router.post("/questions")
async def generate_questions(
    req: GenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = LLMService(current_user.token)
    return await service.generate_questions(
        user_id=current_user.id,
        source_ids=req.source_ids,
        max_questions=req.max_questions,
        question_set_id=req.question_set_id,
    )
