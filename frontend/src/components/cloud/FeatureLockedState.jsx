import React from 'react';
import { Link } from 'react-router-dom';
import { CSP_LABELS } from '../../hooks/useCloudAvailability';

const ANCHOR_BY_GAP = {
  gcp_billing_export_missing: 'byoc-gcp-billing',
  azure_sp_missing: 'byoc-azure-compute',
};

export default function FeatureLockedState({
  featureLabel = 'this feature',
  lockedProviders = [],
  className = '',
}) {
  const list = Array.isArray(lockedProviders) ? lockedProviders : [];
  if (!list.length) return null;

  const primary = list[0];
  const gap = primary?.setup_gaps?.[0] || {};
  const cspLabel = CSP_LABELS[primary.csp] || primary.csp;
  const anchor = ANCHOR_BY_GAP[gap.code] || 'byoc-section';

  return (
    <div className={`feature-locked-state ${className}`.trim()} role="alert">
      <h3>{cspLabel} is blocked for {featureLabel}</h3>
      <p>
        {gap.message || `Complete BYOC setup for ${cspLabel} before using ${featureLabel}.`}
      </p>
      <p className="feature-locked-state__hint">
        Storage and Security may still work. This block only applies to features that need additional credentials.
      </p>
      <Link to={`/dashboard/settings#${anchor}`} className="btn-connect-save">
        Complete setup in Settings
      </Link>
    </div>
  );
}
