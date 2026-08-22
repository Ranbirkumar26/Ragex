from app.contracts import DecisionEnvelope
from app.data.static_repository import StaticPricingRepository
from app.data.supabase_postgres_repository import SupabasePostgresPricingRepository
from app.data.supabase_repository import SupabasePricingRepository


def test_supabase_product_mapping_matches_static_fixture(
    repository: StaticPricingRepository,
) -> None:
    product = repository.list_products()[0]

    rest_mapped = SupabasePricingRepository.row_to_product(product.__dict__)
    postgres_mapped = SupabasePostgresPricingRepository.row_to_product(product.__dict__)

    assert rest_mapped == product
    assert postgres_mapped == product


def test_supabase_decision_mapping_accepts_jsonb() -> None:
    payload = {
        "decision_id": "dec_test",
        "occurred_at": "2026-08-22T10:00:00+05:30",
        "sku_id": "SKU-1001",
        "channel": "web",
        "region": "IN-MH",
        "context": {
            "inventory": 120,
            "competitor_price_inr": 1199,
            "demand_index": 0.72,
        },
        "proposed_price_inr": 1299,
        "policy_version": "policy-v1",
        "model_version": "sim-v1",
        "trace_id": "trace_test",
        "source": "test",
        "anomaly_mode": "none",
        "guardrail": {"status": "pass", "flags": []},
        "regret": {
            "status": "pending",
            "score_inr": 0,
            "best_price_inr": 0,
            "chosen_reward_inr": 0,
            "best_reward_inr": 0,
            "model_version": "regret-v1",
        },
        "explanation": {"status": "unavailable", "summary": "", "evidence": []},
    }

    rest_mapped = SupabasePricingRepository.row_to_decision({"envelope_json": payload})
    postgres_mapped = SupabasePostgresPricingRepository.row_to_decision({"envelope_json": payload})

    assert isinstance(rest_mapped, DecisionEnvelope)
    assert isinstance(postgres_mapped, DecisionEnvelope)


def test_static_repository_loads_seed_data(repository: StaticPricingRepository) -> None:
    assert len(repository.list_products()) == 4
    assert len(repository.list_historical_events("SKU-1001")) >= 10
