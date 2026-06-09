import React, { useEffect, useState } from "react";
import { fetchSecurityCostPreview } from "../../api";
import { usePreferences } from "../../context/PreferencesContext";
import { CSP_LABELS } from "../../hooks/useCloudAvailability";

export default function SecurityCostPreview({
  fileSizeMb,
  encryptionMethod = "server-side",
  selectedCsp,
  enableReplication = false,
  token,
  compact = false,
}) {
  const { formatCurrency } = usePreferences();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fileSizeMb || !token) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const data = await fetchSecurityCostPreview(token, {
          file_size_mb: fileSizeMb,
          encryption_method: encryptionMethod,
          selected_csp: selectedCsp || undefined,
          enable_replication: enableReplication,
        });
        if (!cancelled) {
          setPreview(data);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("Could not load cost preview");
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [fileSizeMb, encryptionMethod, selectedCsp, enableReplication, token]);

  if (error) {
    return <p className="security-cost-preview-error">{error}</p>;
  }
  if (!preview) {
    return <p className="security-cost-preview-loading">Calculating vault storage cost…</p>;
  }

  return (
    <div className={`security-cost-preview${compact ? " security-cost-preview--compact" : ""}`}>
      {!compact && (
        <>
          <h4 className="zenith-wizard-section-title">Vault storage cost</h4>
          <p className="zenith-wizard-section-desc">
            Secure vault uses standard (hot) storage. Replication adds about 20% for backup copies.
          </p>
        </>
      )}

      <div className="security-cost-summary">
        <div className="security-cost-line">
          <span>Base storage</span>
          <span>{formatCurrency(preview.base_monthly_usd, 4)}/mo</span>
        </div>
        {preview.replication_monthly_usd != null && preview.replication_monthly_usd > 0 && (
          <div className="security-cost-line">
            <span>Replication (+20%)</span>
            <span>{formatCurrency(preview.replication_monthly_usd, 4)}/mo</span>
          </div>
        )}
        <div className="security-cost-line security-cost-line--total">
          <span>Total</span>
          <span>{formatCurrency(preview.total_monthly_usd, 4)}/mo</span>
        </div>
      </div>

      <h4 className="zenith-wizard-section-title security-cost-cross-title">
        Same protection, three clouds
      </h4>
      <div className="security-cost-cross-table-wrap">
        <table className="security-cost-cross-table">
          <thead>
            <tr>
              <th>Cloud</th>
              <th>Service</th>
              <th>Est. / month</th>
            </tr>
          </thead>
          <tbody>
            {preview.cross_cloud?.map((row) => (
              <tr key={row.csp} className={row.is_recommended ? "is-best" : ""}>
                <td>
                  {CSP_LABELS[row.csp] || row.csp}
                  {row.is_recommended && (
                    <span className="security-cost-best-badge">Best value</span>
                  )}
                </td>
                <td>{row.service_name}</td>
                <td>{formatCurrency(row.total_monthly_usd, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
