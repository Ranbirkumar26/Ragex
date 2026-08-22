from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.contracts import DecisionEnvelope
from app.errors import DataUnavailableError


@dataclass(frozen=True)
class Product:
    sku_id: str
    name: str
    category: str
    floor_price_inr: float
    ceiling_price_inr: float
    base_price_inr: float
    unit_cost_inr: float
    channel: str
    region: str


@dataclass(frozen=True)
class HistoricalEvent:
    event_id: str
    occurred_at: datetime
    sku_id: str
    channel: str
    region: str
    inventory: int
    competitor_price_inr: float
    demand_index: float
    price_inr: float
    units_sold: int
    margin_inr: float
    reward_inr: float


@dataclass(frozen=True)
class PolicyDocument:
    doc_id: str
    title: str
    path: Path
    content: str


class PricingRepository(Protocol):
    def list_products(self) -> list[Product]:
        raise NotImplementedError

    def get_product(self, sku_id: str) -> Product:
        raise NotImplementedError

    def list_historical_events(self, sku_id: str | None = None) -> list[HistoricalEvent]:
        raise NotImplementedError

    def list_decisions(
        self, limit: int = 100, flagged_only: bool = False
    ) -> list[DecisionEnvelope]:
        raise NotImplementedError

    def append_decisions(self, decisions: list[DecisionEnvelope]) -> None:
        raise NotImplementedError

    def list_policy_documents(self) -> list[PolicyDocument]:
        raise NotImplementedError


def get_repository(settings: Settings) -> PricingRepository:
    if settings.repository_mode == "static":
        from app.data.static_repository import StaticPricingRepository

        return StaticPricingRepository(settings.data_dir)

    if (
        settings.repository_mode in {"supabase", "supabase_postgres"}
        and not settings.has_supabase
        and not settings.has_supabase_postgres
    ):
        raise DataUnavailableError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_DB_URL are required"
        )

    if settings.repository_mode in {"auto", "supabase_postgres"} and settings.has_supabase_postgres:
        from app.data.supabase_postgres_repository import SupabasePostgresPricingRepository

        try:
            return SupabasePostgresPricingRepository.from_settings(settings)
        except Exception:
            if settings.repository_mode == "supabase_postgres":
                raise

    if settings.repository_mode in {"auto", "supabase"} and settings.has_supabase:
        from app.data.supabase_repository import SupabasePricingRepository

        try:
            return SupabasePricingRepository.from_settings(settings)
        except Exception:
            if settings.repository_mode == "supabase":
                raise

    from app.data.static_repository import StaticPricingRepository

    return StaticPricingRepository(settings.data_dir)
