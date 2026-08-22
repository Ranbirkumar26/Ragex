import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";

const decision = {
  decision_id: "dec_test_001",
  occurred_at: "2026-08-22T10:00:00+05:30",
  sku_id: "SKU-1001",
  channel: "web",
  region: "IN-MH",
  context: {
    inventory: 120,
    competitor_price_inr: 1199,
    demand_index: 0.72
  },
  proposed_price_inr: 700,
  policy_version: "policy-v1",
  model_version: "sim-v1",
  trace_id: "trace_test_001",
  source: "simulator",
  anomaly_mode: "floor_breach",
  guardrail: {
    status: "block",
    flags: [
      {
        code: "floor_breach",
        severity: "critical",
        message: "Proposed price is below approved SKU floor.",
        metric: "proposed_price_inr",
        observed_value: 700,
        threshold: 899,
        policy_ref: "pricing_policy_v1.floor"
      }
    ]
  },
  regret: {
    status: "scored",
    score_inr: 3500,
    best_price_inr: 1299,
    chosen_reward_inr: 12000,
    best_reward_inr: 15500,
    model_version: "regret-v1"
  },
  explanation: {
    status: "grounded",
    summary: "Decision dec_test_001 has floor_breach.",
    evidence: [
      {
        doc_id: "pricing_policy",
        title: "Pricing policy v1",
        snippet: "Floor breaches are critical.",
        score: 0.9,
        policy_ref: "pricing_policy.1"
      }
    ]
  }
};

describe("Dashboard", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders feed rows, filters blocked decisions, and opens detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          generated_at: "2026-08-22T10:00:00+05:30",
          decisions: [decision]
        })
      )
    );

    render(<Dashboard />);

    expect(await screen.findByText("SKU-1001")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "block" }));
    expect(screen.getByText("floor_breach")).toBeInTheDocument();
    await userEvent.click(screen.getByText("SKU-1001"));
    expect(screen.getByRole("complementary", { name: "Decision detail" })).toBeInTheDocument();
    expect(screen.getByText("Pricing policy v1")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          generated_at: "2026-08-22T10:00:00+05:30",
          decisions: []
        })
      )
    );

    render(<Dashboard />);

    expect(await screen.findByText("No decisions yet")).toBeInTheDocument();
  });

  it("renders error state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 503 }))
    );

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText("Feed unavailable")).toBeInTheDocument());
  });
});
