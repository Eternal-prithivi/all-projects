import React, { useState } from "react";
import { lifecyclePolicyLabel } from "../../constants/lifecyclePolicies";
import { usePreferences } from "../../context/PreferencesContext";

const STATUS_LABELS = {
  aligned: "Aligned",
  watch: "Watch",
  action: "Action",
};

const TIER_LABELS = { hot: "Hot", warm: "Warm", cold: "Cold" };

export default function StorageFileInsight({ insight }) {
  const [open, setOpen] = useState(false);
  const { formatCurrency } = usePreferences();

  if (!insight) return <span className="file-insight-na">—</span>;

  const status = insight.status || "aligned";
  const reasons = insight.reasons || [];

  return (
    <div className={`file-insight file-insight--${status}`}>
      <button
        type="button"
        className="file-insight-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className={`file-insight-badge file-insight-badge--${status}`}>
          {STATUS_LABELS[status] || status}
        </span>
        <span className="file-insight-tier">
          {TIER_LABELS[insight.current_tier] || insight.current_tier}
          {insight.planned_tier && insight.planned_tier !== insight.current_tier && (
            <> → {TIER_LABELS[insight.planned_tier] || insight.planned_tier}</>
          )}
        </span>
      </button>
      {open && (
        <div className="file-insight-panel">
          <dl className="file-insight-dl">
            <dt>Policy</dt>
            <dd>{lifecyclePolicyLabel(insight.lifecycle_policy)}</dd>
            <dt>Next</dt>
            <dd>{reasons[0] || "Stable"}</dd>
            {insight.monthly_savings_if_moved_usd > 0 && (
              <>
                <dt>If moved</dt>
                <dd>{formatCurrency(insight.monthly_savings_if_moved_usd, 2)}/mo</dd>
              </>
            )}
            {insight.lifetime_savings_usd > 0 && (
              <>
                <dt>Saved so far</dt>
                <dd>{formatCurrency(insight.lifetime_savings_usd, 2)}</dd>
              </>
            )}
            {insight.inactive_days != null && (
              <>
                <dt>Inactive</dt>
                <dd>{insight.inactive_days} days</dd>
              </>
            )}
            {insight.accesses_last_30d != null && (
              <>
                <dt>Downloads (30d)</dt>
                <dd>{insight.accesses_last_30d}</dd>
              </>
            )}
          </dl>
          {insight.blockers?.length > 0 && (
            <p className="file-insight-blockers">
              Blockers: {insight.blockers.map((b) => b.replace(/_/g, " ")).join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
