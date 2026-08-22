from app.contracts import AnomalyMode
from app.data.static_repository import StaticPricingRepository
from app.guardrail import GuardrailService
from app.simulator import BotSimulator


def _fresh_simulator(settings) -> BotSimulator:
    repository = StaticPricingRepository(settings.data_dir)
    guardrail = GuardrailService(repository, settings)
    return BotSimulator(repository, guardrail, seed=9)


def test_simulator_generates_valid_decisions(simulator: BotSimulator) -> None:
    decisions = simulator.generate(4, AnomalyMode.none)

    assert len(decisions) == 4
    assert {decision.guardrail.status for decision in decisions} == {"pass"}


def test_anomaly_modes_trigger_expected_flags(settings) -> None:
    expected = {
        AnomalyMode.floor_breach: "floor_breach",
        AnomalyMode.ceiling_breach: "ceiling_breach",
        AnomalyMode.price_spike: "rolling_zscore",
        AnomalyMode.drift: "rolling_drift",
    }

    for mode, flag_code in expected.items():
        decisions = _fresh_simulator(settings).generate(12, mode)
        codes = {flag.code for decision in decisions for flag in decision.guardrail.flags}
        assert flag_code in codes
