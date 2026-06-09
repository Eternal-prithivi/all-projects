import React, { useEffect, useState } from "react";
import { fetchStorageCostPreview } from "../../api";
import { usePreferences } from "../../context/PreferencesContext";
import { CSP_LABELS } from "../../hooks/useCloudAvailability";

export default function StorageCostPreview({
  fileSizeMb,
  determinedTier,
  userPriority,
  userIntent,
  lifecyclePolicy,
  selectedCsp,
}) {
  const { formatCurrency } = usePreferences();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fileSizeMb || !determinedTier) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchStorageCostPreview({
          file_size_mb: fileSizeMb,
          determined_tier: determinedTier,
          user_priority: userPriority,
          user_intent: userIntent,
          lifecycle_policy: lifecyclePolicy || "auto",
          selected_csp: selectedCsp || undefined,
        });
        if (!cancelled) {
          setPreview(data);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("Could not load cost preview");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fileSizeMb, determinedTier, userPriority, userIntent, lifecyclePolicy, selectedCsp]);

  if (error) {
    return <p className="storage-cost-preview-error">{error}</p>;
  }
  if (!preview) {
    return <p className="storage-cost-preview-loading">Calculating 12-month cost forecast…</p>;
  }

  const keepHot = preview.scenarios?.find((s) => s.id === "keep_hot");
  const policyScenario = preview.scenarios?.find((s) => s.id !== "keep_hot");

  return (
    <div className="storage-cost-preview">
      <h4 className="zenith-wizard-section-title">Cost forecast (12 months)</h4>
      <p className="zenith-wizard-section-desc">
        Compare keeping fast access vs your lifecycle policy. Zenith uses real tier pricing
        across AWS, GCP, and Azure.
      </p>

      <div className="storage-cost-scenario-grid">
        {preview.scenarios?.map((scenario) => (
          <div
            key={scenario.id}
            className={`storage-cost-scenario-card${
              scenario.id !== "keep_hot" ? " is-recommended" : ""
            }`}
          >
            <span className="storage-cost-scenario-label">{scenario.label}</span>
            <span className="storage-cost-scenario-amount">
              {formatCurrency(scenario.twelve_month_usd, 2)}
            </span>
            <span className="storage-cost-scenario-sub">
              {formatCurrency(scenario.monthly_usd, 2)}/mo avg
            </span>
          </div>
        ))}
      </div>

      {preview.estimated_12_month_savings_usd > 0 && policyScenario && keepHot && (
        <p className="storage-cost-savings-banner">
          Estimated savings with your policy:{" "}
          <strong>{formatCurrency(preview.estimated_12_month_savings_usd, 2)}</strong> over 12
          months vs keep-hot
        </p>
      )}

      <h4 className="zenith-wizard-section-title storage-cost-cross-title">
        Same tier, three clouds ({preview.determined_tier})
      </h4>
      <div className="storage-cost-cross-table-wrap">
        <table className="storage-cost-cross-table">
          <thead>
            <tr>
              <th>Cloud</th>
              <th>Service</th>
              <th>$/GB</th>
              <th>Est. / month</th>
            </tr>
          </thead>
          <tbody>
            {preview.cross_cloud?.map((row) => (
              <tr key={row.csp} className={row.is_recommended ? "is-best" : ""}>
                <td>
                  {CSP_LABELS[row.csp] || row.csp}
                  {row.is_recommended && (
                    <span className="storage-cost-best-badge">Best value</span>
                  )}
                </td>
                <td>{row.service_name}</td>
                <td>${Number(row.price_per_gb).toFixed(4)}</td>
                <td>{formatCurrency(row.monthly_cost_usd, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
