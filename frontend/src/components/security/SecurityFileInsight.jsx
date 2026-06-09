import React, { useState } from "react";
import { usePreferences } from "../../context/PreferencesContext";

const STATUS_LABELS = {
  protected: "Protected",
  watch: "Watch",
  action: "Action",
};

const RISK_LABELS = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

export default function SecurityFileInsight({ insight, file }) {
  const [open, setOpen] = useState(false);
  const { formatCurrency } = usePreferences();

  const data = insight || file?.insight;
  if (!data) return <span className="security-file-insight-na">—</span>;

  const status = data.status || "protected";
  const reasons = data.reasons || [];
  const steps = data.recommended_steps || [];

  return (
    <div className={`security-file-insight security-file-insight--${status}`}>
      <button
        type="button"
        className="security-file-insight-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className={`security-file-insight-badge security-file-insight-badge--${status}`}>
          {STATUS_LABELS[status] || status}
        </span>
        <span className="security-file-insight-risk">
          {RISK_LABELS[data.risk_level] || data.risk_level}
        </span>
      </button>
      {open && (
        <div className="security-file-insight-panel">
          <dl className="security-file-insight-dl">
            <dt>Encryption</dt>
            <dd>{data.encryption_method || "—"}</dd>
            {data.inactive_days != null && (
              <>
                <dt>Last activity</dt>
                <dd>{data.inactive_days} days ago</dd>
              </>
            )}
            {data.monthly_cost_usd > 0 && (
              <>
                <dt>Est. cost</dt>
                <dd>{formatCurrency(data.monthly_cost_usd, 2)}/mo</dd>
              </>
            )}
            {data.ml_scan_score != null && (
              <>
                <dt>ML risk score</dt>
                <dd>{Math.round(data.ml_scan_score * 100)}%</dd>
              </>
            )}
          </dl>
          {reasons.length > 0 && (
            <ul className="security-file-insight-reasons">
              {reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          {steps.length > 0 && (
            <p className="security-file-insight-steps">
              <strong>Next:</strong> {steps.join(" · ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
