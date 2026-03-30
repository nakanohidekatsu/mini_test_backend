from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    anthropic_api_key: str
    frontend_url: str = "http://localhost:3000"

    @property
    def allowed_origins(self) -> List[str]:
        origins = []
        for url in self.frontend_url.split(","):
            url = url.strip().rstrip("/")
            if url:
                origins.append(url)
        # always allow local dev
        if "http://localhost:3000" not in origins:
            origins.append("http://localhost:3000")
        return origins

    class Config:
        env_file = ".env"


settings = Settings()
