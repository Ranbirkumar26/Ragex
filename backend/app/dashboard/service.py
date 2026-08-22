from __future__ import annotations

from app.contracts import DecisionEnvelope
from app.data.repository import PricingRepository
from app.rag import ExplanationService
from app.regret import RegretEngine


class DashboardService:
    def __init__(
        self,
        repository: PricingRepository,
        regret_engine: RegretEngine,
        explanation_service: ExplanationService,
    ) -> None:
        self._repository = repository
        self._regret_engine = regret_engine
        self._explanation_service = explanation_service

    def feed(self, limit: int = 100) -> list[DecisionEnvelope]:
        decisions = self._repository.list_decisions(limit=limit)
        return [self._enrich(decision) for decision in decisions]

    def _enrich(self, decision: DecisionEnvelope) -> DecisionEnvelope:
        regret = decision.regret
        if regret.status != "scored":
            regret = self._regret_engine.score(decision)
        enriched = decision.model_copy(update={"regret": regret})
        explanation = enriched.explanation
        if explanation.status == "unavailable":
            explanation = self._explanation_service.explain(enriched)
        return enriched.model_copy(update={"explanation": explanation})
