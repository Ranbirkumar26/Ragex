import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")


class Settings(BaseModel):
    repository_mode: str = Field(default="auto")
    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""
    supabase_schema: str = "public"
    supabase_timeout_seconds: float = 15.0
    vector_backend: str = "memory"
    chroma_path: Path = Field(default=PROJECT_ROOT / "data" / "chroma")
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_dim: int = 768
    rag_top_k: int = 4
    rag_min_score: float = 0.08
    guardrail_window: int = 10
    guardrail_min_samples: int = 5
    guardrail_zscore_threshold: float = 3.0
    guardrail_drift_threshold: float = 0.10
    regret_model_version: str = "regret-v1"
    llm_chain: str = "template"

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def has_supabase_postgres(self) -> bool:
        return bool(self.supabase_db_url)

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = _rooted_path(os.getenv("DATA_DIR", "data"))
        chroma_path = _rooted_path(os.getenv("CHROMA_PATH", str(data_dir / "chroma")))
        return cls(
            repository_mode=os.getenv("REPOSITORY_MODE", "auto"),
            data_dir=data_dir,
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            supabase_db_url=os.getenv("SUPABASE_DB_URL", ""),
            supabase_schema=os.getenv("SUPABASE_SCHEMA", "public"),
            supabase_timeout_seconds=float(os.getenv("SUPABASE_TIMEOUT_SECONDS", "15")),
            vector_backend=os.getenv("VECTOR_BACKEND", "memory"),
            chroma_path=chroma_path,
            embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5"),
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "768")),
            rag_top_k=int(os.getenv("RAG_TOP_K", "4")),
            rag_min_score=float(os.getenv("RAG_MIN_SCORE", "0.08")),
            guardrail_window=int(os.getenv("GUARDRAIL_WINDOW", "10")),
            guardrail_min_samples=int(os.getenv("GUARDRAIL_MIN_SAMPLES", "5")),
            guardrail_zscore_threshold=float(os.getenv("GUARDRAIL_ZSCORE_THRESHOLD", "3.0")),
            guardrail_drift_threshold=float(os.getenv("GUARDRAIL_DRIFT_THRESHOLD", "0.10")),
            regret_model_version=os.getenv("REGRET_MODEL_VERSION", "regret-v1"),
            llm_chain=os.getenv("LLM_CHAIN", "template"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def _rooted_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
