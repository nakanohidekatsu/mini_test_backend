from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.auth import get_current_user, CurrentUser
from app.schemas.quiz import QuizStartRequest, QuizAnswerRequest
from app.services.quiz_service import QuizService

router = APIRouter()


class FinishRequest(BaseModel):
    session_id: str


@router.post("/start")
async def start_quiz(
    req: QuizStartRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuizService(current_user.token)
    return await service.start_session(user_id=current_user.id, req=req)


@router.post("/answer")
async def submit_answer(
    req: QuizAnswerRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuizService(current_user.token)
    return await service.submit_answer(user_id=current_user.id, req=req)


@router.post("/finish")
async def finish_quiz(
    req: FinishRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuizService(current_user.token)
    return await service.finish_session(user_id=current_user.id, session_id=req.session_id)
