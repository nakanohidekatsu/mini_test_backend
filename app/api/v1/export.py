from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.core.auth import get_current_user, CurrentUser
from app.services.question_service import QuestionService

router = APIRouter()


@router.get("/csv")
async def export_csv(current_user: CurrentUser = Depends(get_current_user)):
    service = QuestionService(current_user.token)
    content = await service.export_csv(user_id=current_user.id)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=questions.csv"},
    )


@router.get("/json")
async def export_json(current_user: CurrentUser = Depends(get_current_user)):
    service = QuestionService(current_user.token)
    return await service.export_json(user_id=current_user.id)
