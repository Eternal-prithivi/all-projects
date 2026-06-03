import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Shown when no cloud providers are available for a feature.
 */
export default function CloudAvailabilityBanner({
  featureLabel = 'this feature',
  credentialMode,
  className = '',
}) {
  const isHybrid = credentialMode === 'hybrid';
  const isByoc = credentialMode === 'byoc';
  return (
    <div className={`cloud-availability-empty ${className}`.trim()} role="status">
      <h3>No cloud provider available</h3>
      <p>
        {isByoc && !isHybrid
          ? `Connect at least one cloud account in Settings to use ${featureLabel}.`
          : `Zenith platform credentials are not configured for ${featureLabel}. Contact your administrator or connect your own account (BYOC) in Settings.`}
      </p>
      <Link to="/dashboard/settings" className="btn-primary" style={{ display: 'inline-block', marginTop: '0.75rem' }}>
        Open Settings (BYOC)
      </Link>
    </div>
  );
}
