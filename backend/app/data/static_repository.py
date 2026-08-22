from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.contracts import DecisionEnvelope
from app.data.generate import default_historical_events, default_products
from app.data.repository import HistoricalEvent, PolicyDocument, Product
from app.errors import NotFoundError


class StaticPricingRepository:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._products = self._load_products()
        self._historical_events = self._load_historical_events()
        self._decisions: list[DecisionEnvelope] = []
        self._lock = threading.Lock()

    def list_products(self) -> list[Product]:
        return list(self._products)

    def get_product(self, sku_id: str) -> Product:
        for product in self._products:
            if product.sku_id == sku_id:
                return product
        raise NotFoundError(f"Unknown sku_id {sku_id}")

    def list_historical_events(self, sku_id: str | None = None) -> list[HistoricalEvent]:
        events = self._historical_events
        if sku_id:
            events = [event for event in events if event.sku_id == sku_id]
        return list(events)

    def list_decisions(
        self, limit: int = 100, flagged_only: bool = False
    ) -> list[DecisionEnvelope]:
        with self._lock:
            decisions = list(reversed(self._decisions))
        if flagged_only:
            decisions = [decision for decision in decisions if decision.guardrail.status != "pass"]
        return decisions[:limit]

    def append_decisions(self, decisions: list[DecisionEnvelope]) -> None:
        with self._lock:
            self._decisions.extend(decisions)

    def list_policy_documents(self) -> list[PolicyDocument]:
        corpus_dir = self._data_dir / "corpus"
        if not corpus_dir.exists():
            return []

        documents: list[PolicyDocument] = []
        for path in sorted(corpus_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            title = _extract_title(content, fallback=path.stem.replace("_", " ").title())
            documents.append(
                PolicyDocument(doc_id=path.stem, title=title, path=path, content=content)
            )
        return documents

    def _load_products(self) -> list[Product]:
        path = self._data_dir / "exports" / "products.csv"
        if not path.exists():
            return default_products()

        frame = pd.read_csv(path)
        return [
            Product(
                sku_id=str(row.sku_id),
                name=str(row.name),
                category=str(row.category),
                floor_price_inr=float(row.floor_price_inr),
                ceiling_price_inr=float(row.ceiling_price_inr),
                base_price_inr=float(row.base_price_inr),
                unit_cost_inr=float(row.unit_cost_inr),
                channel=str(row.channel),
                region=str(row.region),
            )
            for row in frame.itertuples(index=False)
        ]

    def _load_historical_events(self) -> list[HistoricalEvent]:
        path = self._data_dir / "exports" / "historical_pricing.csv"
        if not path.exists():
            return default_historical_events(default_products())

        frame = pd.read_csv(path)
        return [
            HistoricalEvent(
                event_id=str(row.event_id),
                occurred_at=datetime.fromisoformat(str(row.occurred_at)),
                sku_id=str(row.sku_id),
                channel=str(row.channel),
                region=str(row.region),
                inventory=int(row.inventory),
                competitor_price_inr=float(row.competitor_price_inr),
                demand_index=float(row.demand_index),
                price_inr=float(row.price_inr),
                units_sold=int(row.units_sold),
                margin_inr=float(row.margin_inr),
                reward_inr=float(row.reward_inr),
            )
            for row in frame.itertuples(index=False)
        ]


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback
