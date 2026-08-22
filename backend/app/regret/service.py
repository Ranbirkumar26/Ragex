from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.config import Settings
from app.contracts import DecisionEnvelope, RegretResult
from app.data.repository import HistoricalEvent, PricingRepository, Product


@dataclass(frozen=True)
class _ModelBundle:
    pipeline: Pipeline
    products: dict[str, Product]


class RegretEngine:
    def __init__(self, repository: PricingRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings
        self._bundle: _ModelBundle | None = None

    def score(self, decision: DecisionEnvelope) -> RegretResult:
        bundle = self._model()
        product = bundle.products[decision.sku_id]
        candidates = np.linspace(product.floor_price_inr, product.ceiling_price_inr, 31)
        frame = pd.DataFrame(
            [self._features(decision, product, float(price)) for price in candidates]
        )
        rewards = bundle.pipeline.predict(frame)
        best_index = int(np.argmax(rewards))
        chosen_frame = pd.DataFrame(
            [self._features(decision, product, decision.proposed_price_inr)]
        )
        best_reward = float(rewards[best_index])
        chosen_reward = self._adjust_out_of_policy_reward(
            float(bundle.pipeline.predict(chosen_frame)[0]),
            decision,
            product,
        )
        regret = max(0.0, best_reward - chosen_reward)
        return RegretResult(
            status="scored",
            score_inr=round(regret, 2),
            best_price_inr=round(float(candidates[best_index]), 2),
            chosen_reward_inr=round(chosen_reward, 2),
            best_reward_inr=round(best_reward, 2),
            model_version=self._settings.regret_model_version,
        )

    def _model(self) -> _ModelBundle:
        if self._bundle is not None:
            return self._bundle

        products = {product.sku_id: product for product in self._repository.list_products()}
        events = self._repository.list_historical_events()
        frame = pd.DataFrame(
            [self._event_features(event, products[event.sku_id]) for event in events]
        )
        target = pd.Series([event.reward_inr for event in events])

        numeric_features = [
            "price_inr",
            "inventory",
            "competitor_price_inr",
            "demand_index",
            "floor_price_inr",
            "ceiling_price_inr",
            "unit_cost_inr",
        ]
        categorical_features = ["sku_id", "category", "channel", "region"]
        transformer = ColumnTransformer(
            transformers=[
                ("numeric", StandardScaler(), numeric_features),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    categorical_features,
                ),
            ],
            remainder="drop",
        )
        pipeline = Pipeline(
            steps=[
                ("features", transformer),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=180,
                        learning_rate=0.05,
                        l2_regularization=0.01,
                        random_state=17,
                    ),
                ),
            ]
        )
        pipeline.fit(frame, target)
        self._bundle = _ModelBundle(pipeline=pipeline, products=products)
        return self._bundle

    def _features(
        self, decision: DecisionEnvelope, product: Product, price_inr: float
    ) -> dict[str, float | int | str]:
        return {
            "sku_id": decision.sku_id,
            "category": product.category,
            "channel": decision.channel,
            "region": decision.region,
            "price_inr": price_inr,
            "inventory": decision.context.inventory,
            "competitor_price_inr": decision.context.competitor_price_inr,
            "demand_index": decision.context.demand_index,
            "floor_price_inr": product.floor_price_inr,
            "ceiling_price_inr": product.ceiling_price_inr,
            "unit_cost_inr": product.unit_cost_inr,
        }

    @staticmethod
    def _event_features(event: HistoricalEvent, product: Product) -> dict[str, float | int | str]:
        return {
            "sku_id": event.sku_id,
            "category": product.category,
            "channel": event.channel,
            "region": event.region,
            "price_inr": event.price_inr,
            "inventory": event.inventory,
            "competitor_price_inr": event.competitor_price_inr,
            "demand_index": event.demand_index,
            "floor_price_inr": product.floor_price_inr,
            "ceiling_price_inr": product.ceiling_price_inr,
            "unit_cost_inr": product.unit_cost_inr,
        }

    @staticmethod
    def _adjust_out_of_policy_reward(
        predicted_reward: float,
        decision: DecisionEnvelope,
        product: Product,
    ) -> float:
        expected_units = max(1.0, decision.context.inventory * decision.context.demand_index * 0.25)
        if decision.proposed_price_inr < product.floor_price_inr:
            return (
                predicted_reward
                - (product.floor_price_inr - decision.proposed_price_inr) * expected_units
            )
        if decision.proposed_price_inr > product.ceiling_price_inr:
            return (
                predicted_reward
                - (decision.proposed_price_inr - product.ceiling_price_inr) * expected_units * 0.6
            )
        return predicted_reward
