from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from app.data.repository import HistoricalEvent, Product


def default_products() -> list[Product]:
    return [
        Product(
            "SKU-1001", "Monsoon Runner Shoes", "footwear", 899, 1899, 1299, 640, "web", "IN-MH"
        ),
        Product("SKU-1002", "Daily Brew Coffee", "kitchen", 349, 899, 549, 210, "web", "IN-KA"),
        Product(
            "SKU-1003",
            "Noise Shield Earbuds",
            "electronics",
            1499,
            3999,
            2499,
            1120,
            "marketplace",
            "IN-DL",
        ),
        Product("SKU-1004", "Smart Desk Lamp", "home", 799, 2299, 1399, 530, "web", "IN-TN"),
    ]


def default_historical_events(products: list[Product], days: int = 30) -> list[HistoricalEvent]:
    rng = np.random.default_rng(7)
    started_at = datetime(2026, 7, 1, 10, tzinfo=UTC)
    events: list[HistoricalEvent] = []

    for product in products:
        for day in range(days):
            demand_index = float(
                np.clip(0.58 + 0.18 * np.sin(day / 4) + rng.normal(0, 0.03), 0.2, 0.95)
            )
            inventory = max(20, int(180 - day * 3 + rng.normal(0, 8)))
            competitor_price = product.base_price_inr * (0.96 + 0.08 * np.sin(day / 6))
            price = product.base_price_inr * (0.92 + 0.18 * np.sin(day / 5))
            price = float(
                np.clip(price, product.floor_price_inr * 1.03, product.ceiling_price_inr * 0.94)
            )
            units = _estimate_units(
                product.base_price_inr, price, competitor_price, demand_index, inventory
            )
            margin = price - product.unit_cost_inr
            reward = units * margin
            events.append(
                HistoricalEvent(
                    event_id=f"hist_{product.sku_id}_{day + 1:03d}",
                    occurred_at=started_at + timedelta(days=day),
                    sku_id=product.sku_id,
                    channel=product.channel,
                    region=product.region,
                    inventory=inventory,
                    competitor_price_inr=round(competitor_price, 2),
                    demand_index=round(demand_index, 3),
                    price_inr=round(price, 2),
                    units_sold=units,
                    margin_inr=round(margin, 2),
                    reward_inr=round(reward, 2),
                )
            )
    return events


def write_seed_files(data_dir: Path) -> None:
    products = default_products()
    events = default_historical_events(products)
    exports_dir = data_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    with (exports_dir / "products.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sku_id",
                "name",
                "category",
                "floor_price_inr",
                "ceiling_price_inr",
                "base_price_inr",
                "unit_cost_inr",
                "channel",
                "region",
            ],
        )
        writer.writeheader()
        for product in products:
            writer.writerow(product.__dict__)

    with (exports_dir / "historical_pricing.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "event_id",
                "occurred_at",
                "sku_id",
                "channel",
                "region",
                "inventory",
                "competitor_price_inr",
                "demand_index",
                "price_inr",
                "units_sold",
                "margin_inr",
                "reward_inr",
            ],
        )
        writer.writeheader()
        for event in events:
            row = event.__dict__.copy()
            row["occurred_at"] = event.occurred_at.isoformat()
            writer.writerow(row)


def _estimate_units(
    base_price: float,
    price: float,
    competitor_price: float,
    demand_index: float,
    inventory: int,
) -> int:
    price_pressure = max(0.35, 1 - abs(price - competitor_price) / competitor_price)
    affordability = (base_price / price) ** 0.55
    stock_pressure = min(1.2, inventory / 120)
    units = 54 * demand_index * price_pressure * affordability * stock_pressure
    return max(4, int(round(units)))
