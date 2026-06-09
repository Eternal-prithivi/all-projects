import React from "react";
import { usePreferences } from "../../context/PreferencesContext";

function gradeColor(grade) {
  if (grade === "A") return "intel-grade-a";
  if (grade === "B") return "intel-grade-b";
  if (grade === "C") return "intel-grade-c";
  return "intel-grade-d";
}

export default function SecurityIntelligenceBar({ summary, loading }) {
  const { formatCurrency } = usePreferences();

  if (loading) {
    return (
      <div className="security-intel-bar zenith-surface" aria-busy="true">
        <p className="security-intel-loading">Loading vault intelligence…</p>
      </div>
    );
  }

  if (!summary) return null;

  const { health, savings } = summary;
  const grade = health?.grade || "—";
  const score = health?.score ?? 0;
  const factors = health?.factors || {};

  return (
    <div className="security-intel-bar zenith-surface zenith-surface--accent-security">
      <div className="security-intel-health">
        <div
          className={`security-intel-grade ${gradeColor(grade)}`}
          aria-label={`Vault health grade ${grade}`}
        >
          <span className="security-intel-grade-letter">{grade}</span>
          <span className="security-intel-grade-score">{score}</span>
        </div>
        <div>
          <h3 className="security-intel-title">Vault health</h3>
          <p className="security-intel-subtitle">{health?.summary}</p>
        </div>
      </div>

      <div className="security-intel-metrics">
        <div className="security-intel-metric">
          <span className="security-intel-metric-value">{factors.awaiting_encryption ?? 0}</span>
          <span className="security-intel-metric-label">Need encryption</span>
        </div>
        <div className="security-intel-metric">
          <span className="security-intel-metric-value">{factors.protected_sensitive ?? 0}</span>
          <span className="security-intel-metric-label">Protected sensitive</span>
        </div>
        <div className="security-intel-metric">
          <span className="security-intel-metric-value">{savings?.stale_files ?? 0}</span>
          <span className="security-intel-metric-label">Stale to review</span>
        </div>
        <div className="security-intel-metric">
          <span className="security-intel-metric-value">
            {formatCurrency(savings?.estimated_monthly_cost_usd ?? 0, 2)}
          </span>
          <span className="security-intel-metric-label">Est. monthly cost</span>
        </div>
      </div>
    </div>
  );
}
