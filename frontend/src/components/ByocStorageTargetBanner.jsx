import React, { useEffect, useState } from 'react';
import apiClient from '../api';
import '../styles/byoc-shared.css';

const CSP_LABEL = { AWS: 'AWS', GCP: 'Google Cloud', Azure: 'Azure' };

function sourceLabel(source) {
  return source === 'byoc' ? 'your account (BYOC)' : 'Zenith platform';
}

function renderTargetLine(info, isSecurity) {
  if (!info) return null;
  const bucketLabel = info.account
    ? `${info.account} / ${info.bucket}`
    : info.bucket;
  return (
  <>
    <li>
      {isSecurity ? 'Vault' : 'Bucket'}: <code>{bucketLabel}</code>
      {info.region && info.region !== '—' ? ` (${info.region})` : ''}
    </li>
    <li>
      Path prefix: <code>{info.key_prefix}</code>
    </li>
    {isSecurity && info.replica_bucket && info.secure_dual_write && (
      <li>
        Replica: <code>{info.replica_bucket}</code>
        {info.replica_region ? ` (${info.replica_region})` : ''}
      </li>
    )}
  </>
  );
}

/**
 * Per-provider storage / secure vault destinations (BYOC + platform hybrid).
 */
export default function ByocStorageTargetBanner({
  variant = 'storage',
  selectedBucket = null,
  selectedRegion = null,
  selectedGcpBucket = null,
  selectedAzureContainer = null,
  bucketCount = null,
  activeCsp = null,
}) {
  const [targets, setTargets] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.get('/byoc/storage-targets');
        if (!cancelled) setTargets(res.data);
      } catch {
        if (!cancelled) setError('Could not load storage destination.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error || !targets) return null;

  const isSecurity = variant === 'security';
  const providers = targets.providers || Object.keys(targets.targets || {});
  const byCsp = targets.targets || {};

  const modeHint =
    targets.mode === 'hybrid'
      ? 'Hybrid: your BYOC clouds plus Zenith platform for others'
      : targets.mode === 'byoc'
        ? 'Your connected cloud accounts'
        : 'Zenith managed storage';

  const showList = providers.filter(
    (csp) => !activeCsp || activeCsp === 'ALL' || activeCsp === csp
  );

  const viewingLabel = (() => {
    if (activeCsp === 'GCP' && selectedGcpBucket) {
      return (
        <>
          Viewing GCS <code>{selectedGcpBucket}</code>
        </>
      );
    }
    if (activeCsp === 'Azure' && selectedAzureContainer) {
      return (
        <>
          Viewing container <code>{selectedAzureContainer}</code>
        </>
      );
    }
    if ((activeCsp === 'AWS' || activeCsp === 'ALL') && selectedBucket) {
      return (
        <>
          Viewing AWS <code>{selectedBucket}</code>
          {selectedRegion && selectedRegion !== 'all' ? ` (${selectedRegion})` : ''}
        </>
      );
    }
    return null;
  })();

  return (
    <div className="byoc-target-banner" role="status">
      <strong>{isSecurity ? 'Secure vault' : 'Storage'}:</strong>{' '}
      <span className="byoc-target-mode">{modeHint}</span>
      {viewingLabel && <p className="byoc-target-hint">{viewingLabel}</p>}
      <ul className="byoc-target-list byoc-target-list--multicsp">
        {showList.map((csp) => {
          const entry = byCsp[csp];
          if (!entry) return null;
          const info = isSecurity ? entry.security : entry.storage;
          return (
            <li key={csp} className="byoc-target-provider-block">
              <strong>{CSP_LABEL[csp] || csp}</strong>
              <span className="byoc-target-source"> ({sourceLabel(entry.credential_source)})</span>
              <ul className="byoc-target-sublist">{renderTargetLine(info, isSecurity)}</ul>
            </li>
          );
        })}
      </ul>
      {(activeCsp === 'AWS' || activeCsp === 'ALL' || !activeCsp) &&
        providers.includes('AWS') &&
        bucketCount != null &&
        bucketCount > 1 && (
        <p className="byoc-target-hint">
          {bucketCount} AWS bucket{bucketCount !== 1 ? 's' : ''} — use the AWS selector above.
        </p>
      )}
      {(activeCsp === 'ALL' || activeCsp === 'GCP' || activeCsp === 'Azure') &&
        providers.length > 1 && (
        <p className="byoc-target-hint">
          Use the cloud filter on the file table to focus one provider&apos;s destination picker.
        </p>
      )}
    </div>
  );
}
