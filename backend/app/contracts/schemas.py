from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AnomalyMode(StrEnum):
    none = "none"
    price_spike = "price_spike"
    floor_breach = "floor_breach"
    ceiling_breach = "ceiling_breach"
    drift = "drift"


class PricingContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    inventory: int = Field(ge=0)
    competitor_price_inr: float = Field(gt=0)
    demand_index: float = Field(ge=0, le=1)


class GuardrailFlag(BaseModel):
    code: str
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    metric: str
    observed_value: float
    threshold: float
    policy_ref: str


class GuardrailResult(BaseModel):
    status: Literal["pass", "review", "block"] = "pass"
    flags: list[GuardrailFlag] = Field(default_factory=list)


class RegretResult(BaseModel):
    status: Literal["pending", "scored", "unavailable"] = "pending"
    score_inr: float = 0
    best_price_inr: float = 0
    chosen_reward_inr: float = 0
    best_reward_inr: float = 0
    model_version: str = "regret-v1"


class ExplanationEvidence(BaseModel):
    doc_id: str
    title: str
    snippet: str
    score: float
    policy_ref: str


class ExplanationResult(BaseModel):
    status: Literal["grounded", "refused", "unavailable"] = "unavailable"
    summary: str = ""
    evidence: list[ExplanationEvidence] = Field(default_factory=list)


class DecisionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    occurred_at: datetime
    sku_id: str
    channel: str
    region: str
    context: PricingContext
    proposed_price_inr: float = Field(gt=0)
    policy_version: str
    model_version: str
    trace_id: str
    source: str
    anomaly_mode: AnomalyMode = AnomalyMode.none
    guardrail: GuardrailResult = Field(default_factory=GuardrailResult)
    regret: RegretResult = Field(default_factory=RegretResult)
    explanation: ExplanationResult = Field(default_factory=ExplanationResult)

    def as_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SimulationRequest(BaseModel):
    count: int = Field(default=50, ge=1, le=500)
    anomaly_mode: AnomalyMode = AnomalyMode.none


class DecisionListResponse(BaseModel):
    decisions: list[DecisionEnvelope]


class DashboardFeedResponse(BaseModel):
    generated_at: datetime
    decisions: list[DecisionEnvelope]
