from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MihiMura"
    VERSION: str = "8.0.0"
    API_V1_STR: str = "/api/v1"
    DEMO_MODE: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Supabase is the single identity + application-data platform.
    SUPABASE_URL: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    # Legacy projects may still expose an anon key. Either publishable or anon works client-side.
    SUPABASE_ANON_KEY: Optional[str] = None
    # Backend-only. Never expose this value to Vite or the browser.
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_REPORTS_BUCKET: str = "mihimura-reports"
    SUPABASE_ATTACHMENTS_BUCKET: str = "mihimura-attachments"
    SUPABASE_KNOWLEDGE_BUCKET: str = "mihimura-knowledge"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768
    RAG_TOP_K: int = 8
    RAG_CHUNK_CHARS: int = 1800
    RAG_CHUNK_OVERLAP_CHARS: int = 220
    RAG_EMBED_BATCH_SIZE: int = 16
    RAG_EMBED_TIMEOUT_MS: int = 45000
    RAG_EMBED_MAX_RETRIES: int = 3
    RAG_EMBED_RETRY_BASE_SECONDS: float = 1.5
    RAG_MAX_EXCERPT_CHARS: int = 1200
    GEMINI_LIVE_MODEL: str = "gemini-3.1-flash-live-preview"
    GEMINI_LIVE_VOICE: str = "Algenib"
    GEMINI_TTS_MODEL: str = "gemini-3.1-flash-tts-preview"
    GEMINI_TTS_VOICE: str = "Algenib"

    SENTINEL_CLIENT_ID: Optional[str] = None
    SENTINEL_CLIENT_SECRET: Optional[str] = None
    SENTINEL_TOKEN_URL: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    SENTINEL_BASE_URL: str = "https://sh.dataspace.copernicus.eu"

    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    MAX_UPLOAD_MB: int = 8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.ALLOWED_ORIGINS.split(",") if x.strip()]

    @property
    def supabase_public_key(self) -> str | None:
        return self.SUPABASE_PUBLISHABLE_KEY or self.SUPABASE_ANON_KEY

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)


settings = Settings()
