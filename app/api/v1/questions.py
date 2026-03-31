from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.auth import get_current_user, CurrentUser
from app.services.question_service import QuestionService
from typing import Optional

router = APIRouter()


class QuestionSetPatch(BaseModel):
    question_set_id: Optional[str] = None


@router.get("")
async def list_questions(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    question_set_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.list_questions(
        user_id=current_user.id,
        status=status,
        category=category,
        difficulty=difficulty,
        tag=tag,
        keyword=keyword,
        question_set_id=question_set_id,
        page=page,
        per_page=per_page,
    )


@router.get("/review")
async def get_review_questions(
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.get_review_questions(user_id=current_user.id, limit=limit)


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.get_question(user_id=current_user.id, question_id=question_id)


@router.patch("/{question_id}/set")
async def patch_question_set(
    question_id: str,
    body: QuestionSetPatch,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.update_question_set(user_id=current_user.id, question_id=question_id, question_set_id=body.question_set_id)


@router.delete("/{question_id}")
async def delete_question(
    question_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.delete_question(user_id=current_user.id, question_id=question_id)
