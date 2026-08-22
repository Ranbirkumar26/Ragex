from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings
from app.contracts import DecisionEnvelope
from app.data.repository import HistoricalEvent, PolicyDocument, Product
from app.errors import NotFoundError


class SupabasePostgresPricingRepository:
    def __init__(self, db_url: str, schema: str = "public") -> None:
        self._db_url = db_url
        self._schema = schema

    @classmethod
    def from_settings(cls, settings: Settings) -> SupabasePostgresPricingRepository:
        return cls(settings.supabase_db_url, settings.supabase_schema)

    def list_products(self) -> list[Product]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                select sku_id, name, category, floor_price_inr, ceiling_price_inr,
                       base_price_inr, unit_cost_inr, channel, region
                from {self._schema}.products
                order by sku_id
                """
            ).fetchall()
        return [self.row_to_product(row) for row in rows]

    def get_product(self, sku_id: str) -> Product:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                select sku_id, name, category, floor_price_inr, ceiling_price_inr,
                       base_price_inr, unit_cost_inr, channel, region
                from {self._schema}.products
                where sku_id = %s
                """,
                (sku_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Unknown sku_id {sku_id}")
        return self.row_to_product(row)

    def list_historical_events(self, sku_id: str | None = None) -> list[HistoricalEvent]:
        sql = f"""
            select event_id, occurred_at, sku_id, channel, region, inventory,
                   competitor_price_inr, demand_index, price_inr, units_sold,
                   margin_inr, reward_inr
            from {self._schema}.historical_pricing_events
        """
        params: tuple[str, ...] = ()
        if sku_id:
            sql += " where sku_id = %s"
            params = (sku_id,)
        sql += " order by occurred_at"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self.row_to_historical_event(row) for row in rows]

    def list_decisions(
        self, limit: int = 100, flagged_only: bool = False
    ) -> list[DecisionEnvelope]:
        where = "where guardrail_status <> 'pass'" if flagged_only else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                select envelope_json
                from {self._schema}.simulator_decisions
                {where}
                order by occurred_at desc
                limit %s
                """,
                (limit,),
            ).fetchall()
        return [self.row_to_decision(row) for row in rows]

    def append_decisions(self, decisions: list[DecisionEnvelope]) -> None:
        if not decisions:
            return
        with self._connect() as connection:
            for decision in decisions:
                connection.execute(
                    f"""
                    insert into {self._schema}.simulator_decisions (
                        decision_id, occurred_at, sku_id, guardrail_status, envelope_json
                    )
                    values (%s, %s, %s, %s, %s)
                    on conflict (decision_id) do update set
                        occurred_at = excluded.occurred_at,
                        sku_id = excluded.sku_id,
                        guardrail_status = excluded.guardrail_status,
                        envelope_json = excluded.envelope_json
                    """,
                    (
                        decision.decision_id,
                        decision.occurred_at,
                        decision.sku_id,
                        decision.guardrail.status,
                        Jsonb(decision.as_json_dict()),
                    ),
                )
                connection.execute(
                    f"delete from {self._schema}.guardrail_flags where decision_id = %s",
                    (decision.decision_id,),
                )
                for flag in decision.guardrail.flags:
                    connection.execute(
                        f"""
                        insert into {self._schema}.guardrail_flags (
                            decision_id, code, severity, message, metric,
                            observed_value, threshold_value, policy_ref
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            decision.decision_id,
                            flag.code,
                            flag.severity,
                            flag.message,
                            flag.metric,
                            flag.observed_value,
                            flag.threshold,
                            flag.policy_ref,
                        ),
                    )

    def list_policy_documents(self) -> list[PolicyDocument]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                select doc_id, title, body
                from {self._schema}.policy_documents
                order by doc_id
                """
            ).fetchall()
        return [
            PolicyDocument(
                doc_id=str(row["doc_id"]),
                title=str(row["title"]),
                path=Path(f"supabase-postgres://{self._schema}/policy_documents/{row['doc_id']}"),
                content=str(row["body"]),
            )
            for row in rows
        ]

    def upsert_products(self, products: list[Product]) -> None:
        with self._connect() as connection:
            for product in products:
                connection.execute(
                    f"""
                    insert into {self._schema}.products (
                        sku_id, name, category, floor_price_inr, ceiling_price_inr,
                        base_price_inr, unit_cost_inr, channel, region
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (sku_id) do update set
                        name = excluded.name,
                        category = excluded.category,
                        floor_price_inr = excluded.floor_price_inr,
                        ceiling_price_inr = excluded.ceiling_price_inr,
                        base_price_inr = excluded.base_price_inr,
                        unit_cost_inr = excluded.unit_cost_inr,
                        channel = excluded.channel,
                        region = excluded.region
                    """,
                    (
                        product.sku_id,
                        product.name,
                        product.category,
                        product.floor_price_inr,
                        product.ceiling_price_inr,
                        product.base_price_inr,
                        product.unit_cost_inr,
                        product.channel,
                        product.region,
                    ),
                )

    def upsert_historical_events(self, events: list[HistoricalEvent]) -> None:
        if not events:
            return
        placeholders = ", ".join(["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"] * len(events))
        params: list[Any] = []
        for event in events:
            params.extend(
                [
                    event.event_id,
                    event.occurred_at,
                    event.sku_id,
                    event.channel,
                    event.region,
                    event.inventory,
                    event.competitor_price_inr,
                    event.demand_index,
                    event.price_inr,
                    event.units_sold,
                    event.margin_inr,
                    event.reward_inr,
                ]
            )
        with self._connect() as connection:
            connection.execute(
                f"""
                insert into {self._schema}.historical_pricing_events (
                    event_id, occurred_at, sku_id, channel, region, inventory,
                    competitor_price_inr, demand_index, price_inr, units_sold,
                    margin_inr, reward_inr
                )
                values {placeholders}
                on conflict (event_id) do update set
                    occurred_at = excluded.occurred_at,
                    sku_id = excluded.sku_id,
                    channel = excluded.channel,
                    region = excluded.region,
                    inventory = excluded.inventory,
                    competitor_price_inr = excluded.competitor_price_inr,
                    demand_index = excluded.demand_index,
                    price_inr = excluded.price_inr,
                    units_sold = excluded.units_sold,
                    margin_inr = excluded.margin_inr,
                    reward_inr = excluded.reward_inr
                """,
                params,
            )

    def upsert_policy_documents(self, documents: list[PolicyDocument]) -> None:
        with self._connect() as connection:
            for document in documents:
                connection.execute(
                    f"""
                    insert into {self._schema}.policy_documents (doc_id, title, body)
                    values (%s, %s, %s)
                    on conflict (doc_id) do update set
                        title = excluded.title,
                        body = excluded.body
                    """,
                    (document.doc_id, document.title, document.content),
                )

    @staticmethod
    def row_to_product(row: Mapping[str, Any]) -> Product:
        return Product(
            sku_id=str(row["sku_id"]),
            name=str(row["name"]),
            category=str(row["category"]),
            floor_price_inr=float(row["floor_price_inr"]),
            ceiling_price_inr=float(row["ceiling_price_inr"]),
            base_price_inr=float(row["base_price_inr"]),
            unit_cost_inr=float(row["unit_cost_inr"]),
            channel=str(row["channel"]),
            region=str(row["region"]),
        )

    @staticmethod
    def row_to_historical_event(row: Mapping[str, Any]) -> HistoricalEvent:
        occurred_at = row["occurred_at"]
        if not isinstance(occurred_at, datetime):
            occurred_at = datetime.fromisoformat(str(occurred_at).replace("Z", "+00:00"))
        return HistoricalEvent(
            event_id=str(row["event_id"]),
            occurred_at=occurred_at,
            sku_id=str(row["sku_id"]),
            channel=str(row["channel"]),
            region=str(row["region"]),
            inventory=int(row["inventory"]),
            competitor_price_inr=float(row["competitor_price_inr"]),
            demand_index=float(row["demand_index"]),
            price_inr=float(row["price_inr"]),
            units_sold=int(row["units_sold"]),
            margin_inr=float(row["margin_inr"]),
            reward_inr=float(row["reward_inr"]),
        )

    @staticmethod
    def row_to_decision(row: Mapping[str, Any]) -> DecisionEnvelope:
        return DecisionEnvelope.model_validate(row["envelope_json"])

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._db_url, row_factory=dict_row)
