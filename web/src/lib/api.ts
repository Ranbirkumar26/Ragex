import { dashboardFeedSchema, decisionListSchema, type AnomalyMode, type DashboardFeed } from "./schemas";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export async function fetchDashboardFeed(): Promise<DashboardFeed> {
  const response = await fetch(`${API_URL}/api/dashboard/feed`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Feed unavailable");
  }
  const payload: unknown = await response.json();
  return dashboardFeedSchema.parse(payload);
}

export async function simulateDecisions(anomalyMode: AnomalyMode, count = 12): Promise<void> {
  const response = await fetch(`${API_URL}/api/simulator/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ count, anomaly_mode: anomalyMode })
  });
  if (!response.ok) {
    throw new Error("Simulator unavailable");
  }
  const payload: unknown = await response.json();
  decisionListSchema.parse(payload);
}
