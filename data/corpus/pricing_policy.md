# Pricing policy v1

Pricing decisions must remain inside the SKU floor and ceiling boundaries. Any floor breach or ceiling breach blocks release until a pricing owner approves it.

Rolling price anomaly checks compare each proposed price against recent SKU history. Absolute z-score values at or above 3.0 require review because they can indicate discount leakage, channel mismatch, or campaign configuration mistakes.

Sustained drift above 10 percent from the prior rolling window requires review even when every individual decision remains inside floor and ceiling limits.

Guardrail status mapping: no flags passes, medium or high severity enters review, critical severity blocks release.
