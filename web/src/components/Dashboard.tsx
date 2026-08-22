"use client";

import { AlertTriangle, BarChart3, Play, RefreshCcw, Shield, Siren } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchDashboardFeed, simulateDecisions } from "@/lib/api";
import type { AnomalyMode, DashboardFeed, DecisionEnvelope } from "@/lib/schemas";
import { Brand } from "./Brand";
import { DecisionTable } from "./DecisionTable";
import { DetailDrawer } from "./DetailDrawer";
import { StatStrip } from "./StatStrip";
import { ThemeToggle } from "./ThemeToggle";

type FeedState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; feed: DashboardFeed };

type StatusFilter = "all" | "pass" | "review" | "block";

export function Dashboard() {
  const [feedState, setFeedState] = useState<FeedState>({ status: "loading" });
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selected, setSelected] = useState<DecisionEnvelope | null>(null);
  const [busyMode, setBusyMode] = useState<AnomalyMode | null>(null);

  async function refresh() {
    try {
      const feed = await fetchDashboardFeed();
      setFeedState({ status: "ready", feed });
    } catch (error) {
      setFeedState({
        status: "error",
        message: error instanceof Error ? error.message : "Feed unavailable"
      });
    }
  }

  useEffect(() => {
    void refresh();
    const handle = window.setInterval(() => {
      void refresh();
    }, 2000);
    return () => window.clearInterval(handle);
  }, []);

  async function runSimulation(anomalyMode: AnomalyMode) {
    setBusyMode(anomalyMode);
    try {
      await simulateDecisions(anomalyMode, anomalyMode === "none" ? 12 : 8);
      await refresh();
    } finally {
      setBusyMode(null);
    }
  }

  const decisions = feedState.status === "ready" ? feedState.feed.decisions : [];
  const filtered = useMemo(() => {
    const visible =
      statusFilter === "all"
        ? decisions
        : decisions.filter((decision) => decision.guardrail.status === statusFilter);
    return [...visible].sort((left, right) => right.regret.score_inr - left.regret.score_inr);
  }, [decisions, statusFilter]);

  return (
    <main className="shell">
      <aside className="sidebar">
        <Brand />
        <nav className="nav" aria-label="Dashboard sections">
          <button className="nav-item active">
            <BarChart3 size={18} />
            Live feed
          </button>
          <button className="nav-item">
            <Shield size={18} />
            Guardrails
          </button>
          <button className="nav-item">
            <Siren size={18} />
            Incidents
          </button>
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h1>Live pricing decisions</h1>
            <p>{feedState.status === "ready" ? `Updated ${formatTime(feedState.feed.generated_at)}` : "Connecting"}</p>
          </div>
          <div className="toolbar">
            <button className="action-button secondary" onClick={refresh}>
              <RefreshCcw size={18} />
              Refresh
            </button>
            <button className="action-button" onClick={() => runSimulation("none")} disabled={busyMode !== null}>
              <Play size={18} />
              Baseline
            </button>
            <button className="action-button" onClick={() => runSimulation("price_spike")} disabled={busyMode !== null}>
              <AlertTriangle size={18} />
              Spike
            </button>
            <button className="action-button" onClick={() => runSimulation("floor_breach")} disabled={busyMode !== null}>
              <Siren size={18} />
              Floor
            </button>
            <ThemeToggle />
          </div>
        </header>

        <StatStrip decisions={decisions} />

        <section className="panel">
          <div className="panel-header">
            <strong>Decision feed</strong>
            <div className="filters">
              {(["all", "pass", "review", "block"] as const).map((item) => (
                <button
                  key={item}
                  className={`filter-button ${statusFilter === item ? "active" : ""}`}
                  onClick={() => setStatusFilter(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          {feedState.status === "loading" ? (
            <StateMessage title="Loading decisions" />
          ) : feedState.status === "error" ? (
            <StateMessage title={feedState.message} />
          ) : filtered.length === 0 ? (
            <StateMessage title="No decisions yet" />
          ) : (
            <DecisionTable decisions={filtered} onSelect={setSelected} />
          )}
        </section>
      </section>

      <nav className="mobile-tabs" aria-label="Mobile sections">
        <button>Feed</button>
        <button>Flags</button>
        <button>Regret</button>
      </nav>

      {selected ? <DetailDrawer decision={selected} onClose={() => setSelected(null)} /> : null}
    </main>
  );
}

function StateMessage({ title }: { title: string }) {
  return (
    <div className="state">
      <p>{title}</p>
    </div>
  );
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}
