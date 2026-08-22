from pathlib import Path

from app.contracts import DecisionEnvelope


def test_decision_sample_matches_contract() -> None:
    sample = Path(__file__).resolve().parents[2] / "contracts" / "decision.sample.json"

    decision = DecisionEnvelope.model_validate_json(sample.read_text(encoding="utf-8"))

    assert decision.decision_id == "dec_001"
    assert decision.context.inventory == 120
    assert decision.guardrail.status == "pass"
    assert decision.regret.status == "scored"
