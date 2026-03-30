from fastapi import APIRouter, Depends, UploadFile, File, Form
from app.core.auth import get_current_user, CurrentUser
from app.services.ocr_service import OCRService

router = APIRouter()


@router.post("/source")
async def parse_source(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    source_name: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = OCRService(current_user.token)
    return await service.parse(
        user_id=current_user.id,
        file=file,
        source_type=source_type,
        source_name=source_name,
    )
