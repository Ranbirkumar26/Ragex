from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import numpy as np

from app.contracts import AnomalyMode, DecisionEnvelope, ExplanationResult, RegretResult
from app.data.repository import PricingRepository, Product
from app.guardrail import GuardrailService


class BotSimulator:
    def __init__(
        self,
        repository: PricingRepository,
        guardrail_service: GuardrailService,
        seed: int = 42,
    ) -> None:
        self._repository = repository
        self._guardrail_service = guardrail_service
        self._rng = np.random.default_rng(seed)

    def generate(
        self, count: int, anomaly_mode: AnomalyMode = AnomalyMode.none
    ) -> list[DecisionEnvelope]:
        products = self._repository.list_products()
        start_at = datetime.now(UTC).replace(microsecond=0)
        generated: list[DecisionEnvelope] = []
        anomaly_product = products[0]

        for index in range(count):
            product = (
                anomaly_product
                if anomaly_mode != AnomalyMode.none
                else products[index % len(products)]
            )
            context = self._context_for(product, index)
            price = self._price_for(product, context, index, anomaly_mode)
            decision = DecisionEnvelope(
                decision_id=f"dec_{uuid4().hex[:12]}",
                occurred_at=start_at + timedelta(seconds=index),
                sku_id=product.sku_id,
                channel=product.channel,
                region=product.region,
                context=context,
                proposed_price_inr=round(price, 2),
                policy_version="policy-v1",
                model_version="sim-v1",
                trace_id=f"trace_{uuid4().hex[:12]}",
                source="simulator",
                anomaly_mode=anomaly_mode,
                regret=RegretResult(status="pending"),
                explanation=ExplanationResult(status="unavailable"),
            )
            evaluated = decision.model_copy(
                update={"guardrail": self._guardrail_service.evaluate(decision)}
            )
            self._repository.append_decisions([evaluated])
            generated.append(evaluated)

        return generated

    def _context_for(self, product: Product, index: int) -> dict[str, float | int]:
        demand_index = float(
            np.clip(0.64 + 0.12 * np.sin(index / 4) + self._rng.normal(0, 0.02), 0.2, 0.95)
        )
        inventory = max(10, int(140 - index * 2 + self._rng.normal(0, 6)))
        competitor_price = product.base_price_inr * (0.96 + 0.06 * np.sin(index / 5))
        return {
            "inventory": inventory,
            "competitor_price_inr": round(float(competitor_price), 2),
            "demand_index": round(demand_index, 3),
        }

    def _price_for(
        self,
        product: Product,
        context: dict[str, float | int],
        index: int,
        anomaly_mode: AnomalyMode,
    ) -> float:
        competitor_price = float(context["competitor_price_inr"])
        demand_index = float(context["demand_index"])
        normal = competitor_price * (0.98 + 0.08 * demand_index) + self._rng.normal(
            0, product.base_price_inr * 0.015
        )
        normal = float(
            np.clip(normal, product.floor_price_inr * 1.04, product.ceiling_price_inr * 0.96)
        )

        if anomaly_mode == AnomalyMode.floor_breach:
            return product.floor_price_inr * 0.82
        if anomaly_mode == AnomalyMode.ceiling_breach:
            return product.ceiling_price_inr * 1.16
        if anomaly_mode == AnomalyMode.price_spike:
            return product.ceiling_price_inr * 0.985
        if anomaly_mode == AnomalyMode.drift:
            return float(
                np.clip(
                    product.base_price_inr * (1 + 0.045 * index),
                    product.floor_price_inr * 1.04,
                    product.ceiling_price_inr * 0.98,
                )
            )
        return normal
