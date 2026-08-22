from app.contracts import AnomalyMode
from app.rag import ExplanationService
from app.simulator import BotSimulator


def test_explanation_is_grounded_for_flagged_decision(
    simulator: BotSimulator,
    explanation: ExplanationService,
) -> None:
    decision = simulator.generate(1, AnomalyMode.floor_breach)[0]

    result = explanation.explain(decision)

    assert result.status == "grounded"
    assert result.evidence
    assert "floor" in result.evidence[0].snippet.lower()


def test_explanation_refuses_unrelated_question(explanation: ExplanationService) -> None:
    result = explanation.answer_question("How do I book train tickets?")

    assert result.status == "refused"
    assert result.evidence == []
