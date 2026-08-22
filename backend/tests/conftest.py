from pathlib import Path

import pytest

from app.config import Settings
from app.data.static_repository import StaticPricingRepository
from app.guardrail import GuardrailService
from app.rag import ExplanationService, PolicyRetriever
from app.regret import RegretEngine
from app.simulator import BotSimulator

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        repository_mode="static",
        data_dir=ROOT / "data",
        vector_backend="memory",
        rag_min_score=0.08,
    )


@pytest.fixture
def repository(settings: Settings) -> StaticPricingRepository:
    return StaticPricingRepository(settings.data_dir)


@pytest.fixture
def guardrail(repository: StaticPricingRepository, settings: Settings) -> GuardrailService:
    return GuardrailService(repository, settings)


@pytest.fixture
def simulator(repository: StaticPricingRepository, guardrail: GuardrailService) -> BotSimulator:
    return BotSimulator(repository, guardrail, seed=3)


@pytest.fixture
def regret(repository: StaticPricingRepository, settings: Settings) -> RegretEngine:
    return RegretEngine(repository, settings)


@pytest.fixture
def explanation(repository: StaticPricingRepository, settings: Settings) -> ExplanationService:
    return ExplanationService(PolicyRetriever(repository, settings), settings)
