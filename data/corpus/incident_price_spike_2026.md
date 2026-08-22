# Incident 2026-07 price spike

An automated repricer increased electronics prices after competitor feed latency produced stale values. The incident pattern showed a high z-score against recent SKU history while still staying under the ceiling.

The mitigation is to review decisions with large z-score movement and compare them with current competitor price and demand index before release.
