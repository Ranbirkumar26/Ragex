from __future__ import annotations

import statistics

from app.config import Settings
from app.contracts import DecisionEnvelope, GuardrailFlag, GuardrailResult
from app.data.repository import PricingRepository, Product


class GuardrailService:
    def __init__(self, repository: PricingRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def evaluate(self, decision: DecisionEnvelope) -> GuardrailResult:
        product = self._repository.get_product(decision.sku_id)
        historical_prices = [
            event.price_inr for event in self._repository.list_historical_events(decision.sku_id)
        ]
        recent_decisions = [
            item.proposed_price_inr
            for item in reversed(self._repository.list_decisions(limit=500))
            if item.sku_id == decision.sku_id
        ]
        prior_prices = historical_prices + recent_decisions

        flags = [
            *self._floor_ceiling_flags(decision, product),
            *self._zscore_flags(decision, prior_prices),
            *self._drift_flags(decision, prior_prices),
        ]
        flags.sort(key=lambda flag: _SEVERITY_RANK[flag.severity], reverse=True)
        if any(flag.severity == "critical" for flag in flags):
            status = "block"
        elif flags:
            status = "review"
        else:
            status = "pass"
        return GuardrailResult(status=status, flags=flags)

    def _floor_ceiling_flags(
        self, decision: DecisionEnvelope, product: Product
    ) -> list[GuardrailFlag]:
        price = decision.proposed_price_inr
        flags: list[GuardrailFlag] = []
        if price < product.floor_price_inr:
            flags.append(
                GuardrailFlag(
                    code="floor_breach",
                    severity="critical",
                    message="Proposed price is below approved SKU floor.",
                    metric="proposed_price_inr",
                    observed_value=price,
                    threshold=product.floor_price_inr,
                    policy_ref="pricing_policy_v1.floor",
                )
            )
        if price > product.ceiling_price_inr:
            flags.append(
                GuardrailFlag(
                    code="ceiling_breach",
                    severity="critical",
                    message="Proposed price is above approved SKU ceiling.",
                    metric="proposed_price_inr",
                    observed_value=price,
                    threshold=product.ceiling_price_inr,
                    policy_ref="pricing_policy_v1.ceiling",
                )
            )
        return flags

    def _zscore_flags(
        self, decision: DecisionEnvelope, prior_prices: list[float]
    ) -> list[GuardrailFlag]:
        window = prior_prices[-self._settings.guardrail_window :]
        if len(window) < self._settings.guardrail_min_samples:
            return []

        mean = statistics.fmean(window)
        stdev = statistics.pstdev(window)
        if stdev == 0:
            return []

        zscore = (decision.proposed_price_inr - mean) / stdev
        if abs(zscore) < self._settings.guardrail_zscore_threshold:
            return []

        return [
            GuardrailFlag(
                code="rolling_zscore",
                severity="high",
                message="Proposed price is outside the rolling SKU price band.",
                metric="rolling_price_zscore",
                observed_value=round(zscore, 3),
                threshold=self._settings.guardrail_zscore_threshold,
                policy_ref="pricing_policy_v1.rolling_zscore",
            )
        ]

    def _drift_flags(
        self, decision: DecisionEnvelope, prior_prices: list[float]
    ) -> list[GuardrailFlag]:
        needed = self._settings.guardrail_min_samples * 2
        if len(prior_prices) < needed:
            return []

        recent = [
            *prior_prices[-(self._settings.guardrail_min_samples - 1) :],
            decision.proposed_price_inr,
        ]
        baseline = prior_prices[-needed : -self._settings.guardrail_min_samples]
        recent_mean = statistics.fmean(recent)
        baseline_mean = statistics.fmean(baseline)
        if baseline_mean == 0:
            return []

        drift = (recent_mean - baseline_mean) / baseline_mean
        if abs(drift) < self._settings.guardrail_drift_threshold:
            return []

        return [
            GuardrailFlag(
                code="rolling_drift",
                severity="medium",
                message="Recent proposed prices drifted from the prior rolling window.",
                metric="rolling_price_drift",
                observed_value=round(drift, 3),
                threshold=self._settings.guardrail_drift_threshold,
                policy_ref="pricing_policy_v1.drift",
            )
        ]


_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
