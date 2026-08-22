import type { DecisionEnvelope } from "@/lib/schemas";

interface DecisionTableProps {
  decisions: DecisionEnvelope[];
  onSelect: (decision: DecisionEnvelope) => void;
}

export function DecisionTable({ decisions, onSelect }: DecisionTableProps) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Decision</th>
            <th>SKU</th>
            <th>Status</th>
            <th>Price</th>
            <th>Regret</th>
            <th>Flags</th>
            <th>Trace</th>
          </tr>
        </thead>
        <tbody>
          {decisions.map((decision) => (
            <tr key={decision.decision_id} onClick={() => onSelect(decision)}>
              <td title={decision.decision_id}>{shorten(decision.decision_id)}</td>
              <td>{decision.sku_id}</td>
              <td>
                <span className={`pill ${decision.guardrail.status}`}>{decision.guardrail.status}</span>
              </td>
              <td>{formatInr(decision.proposed_price_inr)}</td>
              <td>{formatInr(decision.regret.score_inr)}</td>
              <td>{decision.guardrail.flags.map((flag) => flag.code).join(", ") || "None"}</td>
              <td title={decision.trace_id}>{shorten(decision.trace_id)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function shorten(value: string): string {
  return value.length > 14 ? `${value.slice(0, 14)}...` : value;
}

function formatInr(value: number): string {
  return `Rs ${Math.round(value).toLocaleString("en-IN")}`;
}
