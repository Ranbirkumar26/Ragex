import { z } from "zod";

export const guardrailFlagSchema = z.object({
  code: z.string(),
  severity: z.enum(["low", "medium", "high", "critical"]),
  message: z.string(),
  metric: z.string(),
  observed_value: z.number(),
  threshold: z.number(),
  policy_ref: z.string()
});

export const guardrailResultSchema = z.object({
  status: z.enum(["pass", "review", "block"]),
  flags: z.array(guardrailFlagSchema)
});

export const regretResultSchema = z.object({
  status: z.enum(["pending", "scored", "unavailable"]),
  score_inr: z.number(),
  best_price_inr: z.number(),
  chosen_reward_inr: z.number(),
  best_reward_inr: z.number(),
  model_version: z.string()
});

export const explanationEvidenceSchema = z.object({
  doc_id: z.string(),
  title: z.string(),
  snippet: z.string(),
  score: z.number(),
  policy_ref: z.string()
});

export const explanationResultSchema = z.object({
  status: z.enum(["grounded", "refused", "unavailable"]),
  summary: z.string(),
  evidence: z.array(explanationEvidenceSchema)
});

export const pricingContextSchema = z
  .object({
    inventory: z.number(),
    competitor_price_inr: z.number(),
    demand_index: z.number()
  })
  .passthrough();

export const anomalyModeSchema = z.enum([
  "none",
  "price_spike",
  "floor_breach",
  "ceiling_breach",
  "drift"
]);

export const decisionEnvelopeSchema = z.object({
  decision_id: z.string(),
  occurred_at: z.string(),
  sku_id: z.string(),
  channel: z.string(),
  region: z.string(),
  context: pricingContextSchema,
  proposed_price_inr: z.number(),
  policy_version: z.string(),
  model_version: z.string(),
  trace_id: z.string(),
  source: z.string(),
  anomaly_mode: anomalyModeSchema,
  guardrail: guardrailResultSchema,
  regret: regretResultSchema,
  explanation: explanationResultSchema
});

export const dashboardFeedSchema = z.object({
  generated_at: z.string(),
  decisions: z.array(decisionEnvelopeSchema)
});

export const decisionListSchema = z.object({
  decisions: z.array(decisionEnvelopeSchema)
});

export type AnomalyMode = z.infer<typeof anomalyModeSchema>;
export type DecisionEnvelope = z.infer<typeof decisionEnvelopeSchema>;
export type DashboardFeed = z.infer<typeof dashboardFeedSchema>;
