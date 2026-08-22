from app.contracts import AnomalyMode
from app.regret import RegretEngine
from app.simulator import BotSimulator


def test_regret_scores_off_optimal_price(
    simulator: BotSimulator,
    regret: RegretEngine,
) -> None:
    decision = simulator.generate(1, AnomalyMode.floor_breach)[0]

    result = regret.score(decision)

    assert result.status == "scored"
    assert result.score_inr > 0
    assert result.best_price_inr != decision.proposed_price_inr
