from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import PROJECT_ROOT, get_settings
from app.data.generate import default_historical_events, default_products
from app.data.static_repository import StaticPricingRepository
from app.data.supabase_postgres_repository import SupabasePostgresPricingRepository
from app.data.supabase_repository import SupabasePricingRepository


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    settings = get_settings()
    if not settings.has_supabase and not settings.has_supabase_postgres:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_DB_URL are required"
        )

    products = default_products()
    repository = (
        SupabasePostgresPricingRepository.from_settings(settings)
        if settings.has_supabase_postgres
        else SupabasePricingRepository.from_settings(settings)
    )
    static_repository = StaticPricingRepository(settings.data_dir)

    repository.upsert_products(products)
    print(f"seeded products: {len(products)}")
    historical_events = default_historical_events(products)
    repository.upsert_historical_events(historical_events)
    print(f"seeded historical events: {len(historical_events)}")
    policy_documents = static_repository.list_policy_documents()
    repository.upsert_policy_documents(policy_documents)
    print(f"seeded policy documents: {len(policy_documents)}")


if __name__ == "__main__":
    main()
