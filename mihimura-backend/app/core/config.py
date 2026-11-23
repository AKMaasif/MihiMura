from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MihiMura"
    VERSION: str = "8.0.0"
    API_V1_STR: str = "/api/v1"
    DEMO_MODE: bool = False
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

    # Names are explicit because model availability depends on the provider account.
    XAI_API_KEY: Optional[str] = None
    XAI_MODEL: str = ""
    XAI_VISION_MODEL: str = ""
    META_API_KEY: Optional[str] = None
    META_MODEL: str = ""
    META_VISION_MODEL: str = ""

    GEMINI_API_KEY: Optional[str] = None
    # Model tiers. Each list is tried in order; a model that is unavailable for
    # this API key (no quota, not found) is skipped automatically.
    # Reasoning: Decision Support, Full Report and Crop Vision.
    GEMINI_REASONING_MODELS: str = "gemini-4-argon,gemini-3.8-flash,gemini-2.5-flash"
    # Fast: Simple Chat and report translation.
    GEMINI_FAST_MODELS: str = "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-2.5-flash"
    # Legacy single-model setting, kept as the last fallback in both tiers.
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
    GEMINI_LIVE_MODEL: str = "gemini-3.8-live"
    GEMINI_LIVE_VOICE: str = "Algenib"
    GEMINI_TTS_MODEL: str = "gemini-3.8-flash-tts"
    GEMINI_TTS_VOICE: str = "Algenib"

    SENTINEL_CLIENT_ID: Optional[str] = None
    SENTINEL_CLIENT_SECRET: Optional[str] = None
    SENTINEL_TOKEN_URL: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    SENTINEL_BASE_URL: str = "https://sh.dataspace.copernicus.eu"

    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    MAX_UPLOAD_MB: int = 8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @staticmethod
    def _split(value: str) -> list[str]:
        return [x.strip() for x in (value or "").split(",") if x.strip()]

    @property
    def reasoning_models(self) -> list[str]:
        return self._split(self.GEMINI_REASONING_MODELS) + [self.GEMINI_MODEL]

    @property
    def fast_models(self) -> list[str]:
        return self._split(self.GEMINI_FAST_MODELS) + [self.GEMINI_MODEL]

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
