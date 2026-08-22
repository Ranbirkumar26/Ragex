from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings


def test_api_simulate_list_score_and_feed(settings: Settings) -> None:
    app = create_app(settings)
    client = TestClient(app)

    simulated = client.post(
        "/api/simulator/decisions",
        json={"count": 3, "anomaly_mode": "floor_breach"},
    )
    assert simulated.status_code == 200
    decision = simulated.json()["decisions"][0]
    assert decision["guardrail"]["status"] == "block"

    listed = client.get("/api/decisions?flagged_only=true")
    assert listed.status_code == 200
    assert len(listed.json()["decisions"]) == 3

    scored = client.post("/api/regret/score", json=decision)
    assert scored.status_code == 200
    assert scored.json()["status"] == "scored"

    feed = client.get("/api/dashboard/feed")
    assert feed.status_code == 200
    enriched = feed.json()["decisions"][0]
    assert enriched["regret"]["status"] == "scored"
    assert enriched["explanation"]["status"] == "grounded"
