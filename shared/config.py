from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    base_url: str = Field(default="http://ollama:11434", alias="OLLAMA_BASE_URL")
    model_chat: str = Field(default="qwen2.5:7b-instruct-q4_K_M", alias="OLLAMA_MODEL_CHAT")
    model_embed: str = Field(default="nomic-embed-text", alias="OLLAMA_MODEL_EMBED")
    timeout: int = Field(default=120, alias="OLLAMA_TIMEOUT")
    temperature: float = Field(default=0.2, alias="OLLAMA_TEMPERATURE")
    embedding_dim: int = Field(default=768, alias="EMBEDDING_DIM")


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    host: str = Field(default="redis", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: str = Field(default="", alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB")

    @property
    def dsn(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class QdrantConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    collection: str = Field(default="lvca_knowledge", alias="QDRANT_COLLECTION")


class STTConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    model_size: str = Field(default="large-v3-turbo", alias="STT_MODEL_SIZE")
    device: str = Field(default="auto", alias="STT_DEVICE")
    compute_type: str = Field(default="float16", alias="STT_COMPUTE_TYPE")
    model_cache_dir: str = Field(default="/models", alias="STT_MODEL_CACHE")
    vad_threshold: float = Field(default=0.5, alias="STT_VAD_THRESHOLD")
    host: str = Field(default="0.0.0.0", alias="STT_HOST")
    port: int = Field(default=8001, alias="STT_PORT")  # native mode: 8001


class TTSConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    engine: str = Field(default="piper", alias="TTS_ENGINE")
    model_path: str = Field(default="/models/tts", alias="TTS_MODEL_PATH")
    speaker_wav: Optional[str] = Field(default=None, alias="TTS_SPEAKER_WAV")
    language: str = Field(default="ru", alias="TTS_LANGUAGE")
    device: str = Field(default="cpu", alias="TTS_DEVICE")
    voices_dir: str = Field(default="/voices", alias="VOICES_DIR")
    host: str = Field(default="0.0.0.0", alias="TTS_HOST")
    port: int = Field(default=8003, alias="TTS_PORT")  # native mode: 8003


class DesktopAgentConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    url: str = Field(default="http://host.docker.internal:9100", alias="DESKTOP_AGENT_URL")
    timeout: float = Field(default=10.0, alias="DESKTOP_AGENT_TIMEOUT")
    host: str = Field(default="127.0.0.1", alias="DESKTOP_AGENT_HOST")
    port: int = Field(default=9100, alias="DESKTOP_AGENT_PORT")


class BrainConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    max_context_chunks: int = Field(default=5, alias="BRAIN_MAX_CONTEXT")
    max_agent_steps: int = Field(default=8, alias="BRAIN_MAX_STEPS")
    host: str = Field(default="0.0.0.0", alias="BRAIN_HOST")
    port: int = Field(default=8002, alias="BRAIN_PORT")  # native mode: 8002


class OrchestratorConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    host: str = Field(default="0.0.0.0", alias="ORCH_HOST")
    port: int = Field(default=8000, alias="ORCH_PORT")
    stt_url: str = Field(default="http://stt:8000", alias="STT_SERVICE_URL")
    brain_url: str = Field(default="http://brain:8000", alias="BRAIN_SERVICE_URL")
    tts_url: str = Field(default="http://tts:8000", alias="TTS_SERVICE_URL")


# --- Embedding settings (for rag_chatbot_2 components) ---

class EmbedConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    provider: str = Field(default="ollama", alias="EMBED_PROVIDER")
    model: str = Field(default="nomic-embed-text", alias="EMBED_MODEL")
    dim: int = Field(default=768, alias="EMBED_DIM")
    cache_ttl: int = Field(default=86400, alias="EMBED_CACHE_TTL")  # Redis TTL seconds


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = Field(default="dev", alias="ENV")
    app_name: str = Field(default="LVCA", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="CORS_ORIGINS",
    )

    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")

    # --- Nested configs (lazy-loaded) ---

    _ollama: OllamaConfig | None = None
    _redis: RedisConfig | None = None
    _qdrant: QdrantConfig | None = None
    _stt: STTConfig | None = None
    _tts: TTSConfig | None = None
    _brain: BrainConfig | None = None
    _orchestrator: OrchestratorConfig | None = None
    _embed: EmbedConfig | None = None
    _desktop_agent: DesktopAgentConfig | None = None

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        origins = [o.strip() for o in v.split(",") if o.strip()]
        for origin in origins:
            if origin == "*":
                continue
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"Invalid CORS origin format: {origin}")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ollama(self) -> OllamaConfig:
        if self._ollama is None:
            self._ollama = OllamaConfig()
        return self._ollama

    @property
    def redis(self) -> RedisConfig:
        if self._redis is None:
            self._redis = RedisConfig()
        return self._redis

    @property
    def qdrant(self) -> QdrantConfig:
        if self._qdrant is None:
            self._qdrant = QdrantConfig()
        return self._qdrant

    @property
    def stt(self) -> STTConfig:
        if self._stt is None:
            self._stt = STTConfig()
        return self._stt

    @property
    def tts(self) -> TTSConfig:
        if self._tts is None:
            self._tts = TTSConfig()
        return self._tts

    @property
    def brain(self) -> BrainConfig:
        if self._brain is None:
            self._brain = BrainConfig()
        return self._brain

    @property
    def orchestrator(self) -> OrchestratorConfig:
        if self._orchestrator is None:
            self._orchestrator = OrchestratorConfig()
        return self._orchestrator

    @property
    def embed(self) -> EmbedConfig:
        if self._embed is None:
            self._embed = EmbedConfig()
        return self._embed

    @property
    def desktop_agent(self) -> DesktopAgentConfig:
        if self._desktop_agent is None:
            self._desktop_agent = DesktopAgentConfig()
        return self._desktop_agent

    # Compatibility aliases for rag_chatbot_2 components
    @property
    def EMBED_PROVIDER(self) -> str:
        return self.embed.provider

    @property
    def EMBED_MODEL(self) -> str:
        return self.embed.model

    @property
    def EMBED_DIM(self) -> int:
        return self.embed.dim

    @property
    def VECTOR_BACKEND(self) -> str:
        return "qdrant"

    @property
    def QDRANT_URL(self) -> str:
        return self.qdrant.url

    @property
    def QDRANT_COLLECTION(self) -> str:
        return self.qdrant.collection


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
