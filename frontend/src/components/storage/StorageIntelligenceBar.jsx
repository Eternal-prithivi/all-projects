import React from "react";
import { usePreferences } from "../../context/PreferencesContext";

function gradeColor(grade) {
  if (grade === "A") return "intel-grade-a";
  if (grade === "B") return "intel-grade-b";
  if (grade === "C") return "intel-grade-c";
  return "intel-grade-d";
}

export default function StorageIntelligenceBar({ summary, loading }) {
  const { formatCurrency } = usePreferences();

  if (loading) {
    return (
      <div className="storage-intel-bar zenith-surface" aria-busy="true">
        <p className="storage-intel-loading">Loading storage intelligence…</p>
      </div>
    );
  }

  if (!summary) return null;

  const { health, savings } = summary;
  const grade = health?.grade || "—";
  const score = health?.score ?? 0;

  return (
    <div className="storage-intel-bar zenith-surface">
      <div className="storage-intel-health">
        <div className={`storage-intel-grade ${gradeColor(grade)}`} aria-label={`Health grade ${grade}`}>
          <span className="storage-intel-grade-letter">{grade}</span>
          <span className="storage-intel-grade-score">{score}</span>
        </div>
        <div>
          <h3 className="storage-intel-title">Storage health</h3>
          <p className="storage-intel-subtitle">{health?.summary}</p>
        </div>
      </div>

      <div className="storage-intel-metrics">
        <div className="storage-intel-metric">
          <span className="storage-intel-metric-value">
            {formatCurrency(savings?.lifetime_savings_usd ?? 0, 2)}
          </span>
          <span className="storage-intel-metric-label">Lifetime savings</span>
        </div>
        <div className="storage-intel-metric">
          <span className="storage-intel-metric-value">
            {formatCurrency(savings?.estimated_monthly_opportunity_usd ?? 0, 2)}
          </span>
          <span className="storage-intel-metric-label">Monthly opportunity</span>
        </div>
        <div className="storage-intel-metric">
          <span className="storage-intel-metric-value">{savings?.pending_tier_moves ?? 0}</span>
          <span className="storage-intel-metric-label">Pending moves</span>
        </div>
        <div className="storage-intel-metric">
          <span className="storage-intel-metric-value">{savings?.demotions_this_month ?? 0}</span>
          <span className="storage-intel-metric-label">Demotions (month)</span>
        </div>
        <div className="storage-intel-metric">
          <span className="storage-intel-metric-value">{savings?.promotions_this_month ?? 0}</span>
          <span className="storage-intel-metric-label">Promotions (month)</span>
        </div>
      </div>
    </div>
  );
}
