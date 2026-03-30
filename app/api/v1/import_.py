from fastapi import APIRouter, Depends, UploadFile, File
from app.core.auth import get_current_user, CurrentUser
from app.services.question_service import QuestionService

router = APIRouter()


@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.import_csv(user_id=current_user.id, file=file)


@router.post("/json")
async def import_json(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = QuestionService(current_user.token)
    return await service.import_json(user_id=current_user.id, file=file)
