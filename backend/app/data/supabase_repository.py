from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.contracts import DecisionEnvelope
from app.data.repository import HistoricalEvent, PolicyDocument, Product
from app.errors import DataUnavailableError, NotFoundError


class SupabasePricingRepository:
    def __init__(
        self,
        url: str,
        service_role_key: str,
        schema: str = "public",
        timeout_seconds: float = 15.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._schema = schema
        self._client = httpx.Client(
            base_url=f"{self._url}/rest/v1",
            timeout=timeout_seconds,
            headers={
                "apikey": service_role_key,
                "authorization": f"Bearer {service_role_key}",
                "accept": "application/json",
                "content-type": "application/json",
                "accept-profile": schema,
                "content-profile": schema,
            },
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> SupabasePricingRepository:
        return cls(
            url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            schema=settings.supabase_schema,
            timeout_seconds=settings.supabase_timeout_seconds,
        )

    def list_products(self) -> list[Product]:
        rows = self._request(
            "GET",
            "/products",
            params={"select": "*", "order": "sku_id.asc"},
        )
        return [self.row_to_product(row) for row in rows]

    def get_product(self, sku_id: str) -> Product:
        rows = self._request(
            "GET",
            "/products",
            params={"select": "*", "sku_id": f"eq.{sku_id}", "limit": "1"},
        )
        if not rows:
            raise NotFoundError(f"Unknown sku_id {sku_id}")
        return self.row_to_product(rows[0])

    def list_historical_events(self, sku_id: str | None = None) -> list[HistoricalEvent]:
        params = {"select": "*", "order": "occurred_at.asc"}
        if sku_id:
            params["sku_id"] = f"eq.{sku_id}"
        rows = self._request("GET", "/historical_pricing_events", params=params)
        return [self.row_to_historical_event(row) for row in rows]

    def list_decisions(
        self, limit: int = 100, flagged_only: bool = False
    ) -> list[DecisionEnvelope]:
        params = {
            "select": "envelope_json",
            "order": "occurred_at.desc",
            "limit": str(limit),
        }
        if flagged_only:
            params["guardrail_status"] = "neq.pass"
        rows = self._request("GET", "/simulator_decisions", params=params)
        return [self.row_to_decision(row) for row in rows]

    def append_decisions(self, decisions: list[DecisionEnvelope]) -> None:
        if not decisions:
            return

        self._request(
            "POST",
            "/simulator_decisions",
            params={"on_conflict": "decision_id"},
            headers={"prefer": "resolution=merge-duplicates,return=minimal"},
            json=[
                {
                    "decision_id": decision.decision_id,
                    "occurred_at": decision.occurred_at.isoformat(),
                    "sku_id": decision.sku_id,
                    "guardrail_status": decision.guardrail.status,
                    "envelope_json": decision.as_json_dict(),
                }
                for decision in decisions
            ],
        )
        flags = [
            {
                "decision_id": decision.decision_id,
                "code": flag.code,
                "severity": flag.severity,
                "message": flag.message,
                "metric": flag.metric,
                "observed_value": flag.observed_value,
                "threshold_value": flag.threshold,
                "policy_ref": flag.policy_ref,
            }
            for decision in decisions
            for flag in decision.guardrail.flags
        ]
        if flags:
            self._request(
                "POST",
                "/guardrail_flags",
                headers={"prefer": "return=minimal"},
                json=flags,
            )

    def list_policy_documents(self) -> list[PolicyDocument]:
        rows = self._request(
            "GET",
            "/policy_documents",
            params={"select": "*", "order": "doc_id.asc"},
        )
        return [
            PolicyDocument(
                doc_id=str(row["doc_id"]),
                title=str(row["title"]),
                path=Path(f"supabase://{self._schema}/policy_documents/{row['doc_id']}"),
                content=str(row["body"]),
            )
            for row in rows
        ]

    def upsert_products(self, products: list[Product]) -> None:
        if not products:
            return
        self._request(
            "POST",
            "/products",
            params={"on_conflict": "sku_id"},
            headers={"prefer": "resolution=merge-duplicates,return=minimal"},
            json=[product.__dict__ for product in products],
        )

    def upsert_historical_events(self, events: list[HistoricalEvent]) -> None:
        if not events:
            return
        self._request(
            "POST",
            "/historical_pricing_events",
            params={"on_conflict": "event_id"},
            headers={"prefer": "resolution=merge-duplicates,return=minimal"},
            json=[
                {
                    **event.__dict__,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in events
            ],
        )

    def upsert_policy_documents(self, documents: list[PolicyDocument]) -> None:
        if not documents:
            return
        self._request(
            "POST",
            "/policy_documents",
            params={"on_conflict": "doc_id"},
            headers={"prefer": "resolution=merge-duplicates,return=minimal"},
            json=[
                {"doc_id": document.doc_id, "title": document.title, "body": document.content}
                for document in documents
            ],
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
        envelope = row["envelope_json"]
        if isinstance(envelope, str):
            return DecisionEnvelope.model_validate_json(envelope)
        return DecisionEnvelope.model_validate(envelope)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any | None = None,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                headers=headers,
                json=json,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DataUnavailableError(_supabase_error_message(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise DataUnavailableError(f"Supabase request failed: {exc}") from exc

        if response.status_code == 204 or not response.content:
            return []
        return response.json()


def _supabase_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    return f"Supabase returned {response.status_code}: {payload}"
