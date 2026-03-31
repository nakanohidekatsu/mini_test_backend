from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.auth import get_current_user, CurrentUser
from app.services.question_set_service import QuestionSetService

router = APIRouter()


class QuestionSetBody(BaseModel):
    name: str
    description: str = ""


@router.get("")
async def list_question_sets(current_user: CurrentUser = Depends(get_current_user)):
    service = QuestionSetService(current_user.token)
    return await service.list_sets(user_id=current_user.id)


@router.post("")
async def create_question_set(
    body: QuestionSetBody,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionSetService(current_user.token)
    return await service.create_set(user_id=current_user.id, name=body.name, description=body.description)


@router.put("/{set_id}")
async def update_question_set(
    set_id: str,
    body: QuestionSetBody,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionSetService(current_user.token)
    return await service.update_set(user_id=current_user.id, set_id=set_id, name=body.name, description=body.description)


@router.delete("/{set_id}")
async def delete_question_set(
    set_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionSetService(current_user.token)
    return await service.delete_set(user_id=current_user.id, set_id=set_id)
