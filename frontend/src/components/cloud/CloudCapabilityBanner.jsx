import React from 'react';
import { Link } from 'react-router-dom';
import { CSP_LABELS } from '../../hooks/useCloudAvailability';

const GAP_COPY = {
  azure_sp_missing:
    'Azure Cost, VMs, and Provision are blocked until you add a service principal. Storage and Security still work.',
  gcp_billing_export_missing:
    'GCP Cost is blocked until you add BigQuery billing export dataset and table IDs. Other GCP features still work.',
  aws_credentials_missing: 'Complete your AWS BYOC credentials in Settings.',
  gcp_sa_missing: 'Complete your GCP service account setup in Settings.',
  azure_storage_missing: 'Complete Azure storage credentials in Settings.',
};

const GAP_ANCHOR = {
  azure_sp_missing: 'byoc-azure-compute',
  gcp_billing_export_missing: 'byoc-gcp-billing',
};

/**
 * Shown when a feature has BYOC-connected CSPs that are not ready for this page.
 */
export default function CloudCapabilityBanner({
  feature = 'provision',
  lockedProviders = [],
  className = '',
}) {
  const list = Array.isArray(lockedProviders) ? lockedProviders : [];
  if (!list.length) return null;

  const primary = list[0];
  const gapCode = primary?.gaps?.[0] || primary?.setup_gaps?.[0]?.code;
  const cspLabel = CSP_LABELS[primary.csp] || primary.csp;
  const message =
    GAP_COPY[gapCode] ||
    primary?.setup_gaps?.[0]?.message ||
    `${cspLabel} is connected but not ready for ${feature}.`;

  return (
    <div className={`cloud-capability-banner ${className}`.trim()} role="status">
      <strong>{cspLabel}</strong>
      <p>{message}</p>
      <Link
        to={`/dashboard/settings#${GAP_ANCHOR[gapCode] || 'byoc-section'}`}
        className="btn-secondary cloud-capability-banner__cta"
      >
        Complete setup in Settings
      </Link>
    </div>
  );
}
