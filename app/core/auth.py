from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from app.core.config import settings
import structlog

logger = structlog.get_logger()
security = HTTPBearer()

_supabase = create_client(settings.supabase_url, settings.supabase_service_key)


@dataclass
class CurrentUser:
    id: str
    token: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token = credentials.credentials
    try:
        response = _supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return CurrentUser(id=response.user.id, token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("auth_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# 後方互換
async def get_current_user_id(
    current_user: CurrentUser = Depends(get_current_user),
) -> str:
    return current_user.id
