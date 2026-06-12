import React from 'react';

/**
 * Shows whether the selected CSP uses the user's BYOC account or Zenith platform keys.
 */
export default function CredentialSourceBadge({ source, className = '' }) {
  if (!source) return null;
  const isByoc = source === 'byoc';
  const label = isByoc ? 'Your account' : 'Zenith platform';
  return (
    <span
      className={`credential-source-badge credential-source-badge--${source} ${className}`.trim()}
      title={
        isByoc
          ? 'Operations use credentials from your connected cloud account'
          : 'Operations use Zenith-managed platform credentials'
      }
    >
      {label}
    </span>
  );
}
