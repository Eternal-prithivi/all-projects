import React from "react";
import { Link } from "react-router-dom";

export default function ProvisionSuccessPanel({
  open,
  handoff,
  deploymentId,
  onClose,
  onViewDeployments,
}) {
  if (!open) return null;

  const links = handoff?.handoff_links || {};
  const q = deploymentId ? `?from=provision&deployment=${encodeURIComponent(deploymentId)}` : "";

  return (
    <div className="provision-success-overlay" role="dialog" aria-modal="true">
      <div className="provision-success-modal">
        <h3>Stack deployed successfully</h3>
        <p>
          <strong>{handoff?.deployment_display_name || deploymentId}</strong> on{" "}
          {handoff?.csp || "cloud"} — about ${handoff?.estimated_monthly || "0.00"}/month
        </p>

        {(handoff?.created_resources || []).length > 0 && (
          <ul className="provision-success-resources">
            {handoff.created_resources.map((r) => (
              <li key={`${r.type}-${r.id || r.name}`}>
                {r.type}: {r.name}
                {r.ip ? ` (${r.ip})` : ""}
              </li>
            ))}
          </ul>
        )}

        <p className="provision-success-hint">Use these pages for day-to-day control:</p>
        <div className="provision-success-links">
          {links.vm && (
            <Link to={`/dashboard/vmcluster${q}`} className="btn-provision secondary">
              VM page
            </Link>
          )}
          {links.storage && (
            <Link to={`/dashboard/storage${q}`} className="btn-provision secondary">
              Storage
            </Link>
          )}
          {links.security && (
            <Link to={`/dashboard/security${q}`} className="btn-provision secondary">
              Security
            </Link>
          )}
          {links.cost && (
            <Link to={`/dashboard/costs${q}`} className="btn-provision secondary">
              Cost
            </Link>
          )}
        </div>

        <div className="provision-success-actions">
          <button type="button" className="btn-provision secondary" onClick={onViewDeployments}>
            View in Deployments
          </button>
          <button type="button" className="btn-provision primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
