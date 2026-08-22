import { X } from "lucide-react";

import type { DecisionEnvelope } from "@/lib/schemas";

interface DetailDrawerProps {
  decision: DecisionEnvelope;
  onClose: () => void;
}

export function DetailDrawer({ decision, onClose }: DetailDrawerProps) {
  return (
    <aside className="drawer" aria-label="Decision detail">
      <div className="drawer-header">
        <div>
          <h2>{decision.sku_id}</h2>
          <p>{decision.decision_id}</p>
        </div>
        <button className="icon-button" onClick={onClose} title="Close detail" aria-label="Close detail">
          <X size={18} />
        </button>
      </div>

      <section className="drawer-section">
        <h3>Decision</h3>
        <KeyValue label="Status" value={decision.guardrail.status} />
        <KeyValue label="Price" value={formatInr(decision.proposed_price_inr)} />
        <KeyValue label="Channel" value={decision.channel} />
        <KeyValue label="Region" value={decision.region} />
        <KeyValue label="Trace" value={decision.trace_id} />
      </section>

      <section className="drawer-section">
        <h3>Context</h3>
        <KeyValue label="Inventory" value={decision.context.inventory.toString()} />
        <KeyValue label="Competitor" value={formatInr(decision.context.competitor_price_inr)} />
        <KeyValue label="Demand index" value={decision.context.demand_index.toFixed(3)} />
      </section>

      <section className="drawer-section">
        <h3>Guardrail flags</h3>
        {decision.guardrail.flags.length === 0 ? (
          <p>No flags</p>
        ) : (
          decision.guardrail.flags.map((flag) => (
            <div key={`${flag.code}-${flag.metric}`} className="panel">
              <div className="panel-header">
                <strong>{flag.code}</strong>
                <span className={`pill ${decision.guardrail.status}`}>{flag.severity}</span>
              </div>
              <div className="drawer-section">
                <KeyValue label="Observed" value={flag.observed_value.toString()} />
                <KeyValue label="Threshold" value={flag.threshold.toString()} />
                <KeyValue label="Policy" value={flag.policy_ref} />
              </div>
            </div>
          ))
        )}
      </section>

      <section className="drawer-section">
        <h3>Regret</h3>
        <KeyValue label="Score" value={formatInr(decision.regret.score_inr)} />
        <KeyValue label="Best price" value={formatInr(decision.regret.best_price_inr)} />
        <KeyValue label="Chosen reward" value={formatInr(decision.regret.chosen_reward_inr)} />
        <KeyValue label="Best reward" value={formatInr(decision.regret.best_reward_inr)} />
      </section>

      <section className="drawer-section">
        <h3>Explanation</h3>
        <p>{decision.explanation.summary || "No explanation available"}</p>
        {decision.explanation.evidence.map((item) => (
          <div key={item.policy_ref} className="kv">
            <span>{item.title}</span>
            <span>{item.snippet}</span>
          </div>
        ))}
      </section>
    </aside>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="kv">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function formatInr(value: number): string {
  return `Rs ${Math.round(value).toLocaleString("en-IN")}`;
}
