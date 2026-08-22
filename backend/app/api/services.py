from dataclasses import dataclass

from app.config import Settings
from app.dashboard import DashboardService
from app.data import PricingRepository, get_repository
from app.guardrail import GuardrailService
from app.rag import ExplanationService, PolicyRetriever
from app.regret import RegretEngine
from app.simulator import BotSimulator


@dataclass(frozen=True)
class Services:
    settings: Settings
    repository: PricingRepository
    guardrail: GuardrailService
    simulator: BotSimulator
    regret: RegretEngine
    explanation: ExplanationService
    dashboard: DashboardService


def build_services(settings: Settings) -> Services:
    repository = get_repository(settings)
    guardrail = GuardrailService(repository, settings)
    simulator = BotSimulator(repository, guardrail)
    regret = RegretEngine(repository, settings)
    retriever = PolicyRetriever(repository, settings)
    explanation = ExplanationService(retriever, settings)
    dashboard = DashboardService(repository, regret, explanation)
    return Services(
        settings=settings,
        repository=repository,
        guardrail=guardrail,
        simulator=simulator,
        regret=regret,
        explanation=explanation,
        dashboard=dashboard,
    )
