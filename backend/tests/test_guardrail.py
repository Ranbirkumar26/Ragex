from app.contracts import AnomalyMode, DecisionEnvelope
from app.guardrail import GuardrailService


def _decision(price: float, mode: AnomalyMode = AnomalyMode.none) -> DecisionEnvelope:
    return DecisionEnvelope(
        decision_id=f"test_{price}",
        occurred_at="2026-08-22T10:00:00+05:30",
        sku_id="SKU-1001",
        channel="web",
        region="IN-MH",
        context={"inventory": 120, "competitor_price_inr": 1299, "demand_index": 0.72},
        proposed_price_inr=price,
        policy_version="policy-v1",
        model_version="test",
        trace_id="trace_test",
        source="test",
        anomaly_mode=mode,
    )


def test_normal_price_passes_guardrails(guardrail: GuardrailService) -> None:
    result = guardrail.evaluate(_decision(1299))

    assert result.status == "pass"
    assert result.flags == []


def test_floor_breach_blocks(guardrail: GuardrailService) -> None:
    result = guardrail.evaluate(_decision(700, AnomalyMode.floor_breach))

    assert result.status == "block"
    assert result.flags[0].code == "floor_breach"


def test_ceiling_breach_blocks(guardrail: GuardrailService) -> None:
    result = guardrail.evaluate(_decision(2200, AnomalyMode.ceiling_breach))

    assert result.status == "block"
    assert result.flags[0].code == "ceiling_breach"


def test_price_spike_review_flag(guardrail: GuardrailService) -> None:
    result = guardrail.evaluate(_decision(1870, AnomalyMode.price_spike))

    assert result.status == "review"
    assert any(flag.code == "rolling_zscore" for flag in result.flags)
