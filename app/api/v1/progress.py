from fastapi import APIRouter, Depends
from app.core.auth import get_current_user, CurrentUser
from app.services.progress_service import ProgressService

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(current_user: CurrentUser = Depends(get_current_user)):
    service = ProgressService(current_user.token)
    return await service.get_dashboard(user_id=current_user.id)


@router.get("/stats")
async def get_stats(current_user: CurrentUser = Depends(get_current_user)):
    service = ProgressService(current_user.token)
    return await service.get_stats(user_id=current_user.id)


@router.get("/history")
async def get_history(current_user: CurrentUser = Depends(get_current_user)):
    service = ProgressService(current_user.token)
    return await service.get_history(user_id=current_user.id)
