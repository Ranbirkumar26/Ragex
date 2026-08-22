import { AlertTriangle, IndianRupee, ShieldCheck, Siren } from "lucide-react";
import type { ReactNode } from "react";

import type { DecisionEnvelope } from "@/lib/schemas";

interface StatStripProps {
  decisions: DecisionEnvelope[];
}

export function StatStrip({ decisions }: StatStripProps) {
  const blocked = decisions.filter((decision) => decision.guardrail.status === "block").length;
  const review = decisions.filter((decision) => decision.guardrail.status === "review").length;
  const regret = decisions.reduce((sum, decision) => sum + decision.regret.score_inr, 0);

  return (
    <section className="metric-grid" aria-label="Decision metrics">
      <Metric label="Decisions" value={decisions.length.toString()} icon={<ShieldCheck size={18} />} />
      <Metric label="Review" value={review.toString()} icon={<AlertTriangle size={18} />} />
      <Metric label="Blocked" value={blocked.toString()} icon={<Siren size={18} />} />
      <Metric label="Regret" value={formatInr(regret)} icon={<IndianRupee size={18} />} />
    </section>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <div aria-hidden="true">{icon}</div>
    </div>
  );
}

function formatInr(value: number): string {
  return `Rs ${Math.round(value).toLocaleString("en-IN")}`;
}
