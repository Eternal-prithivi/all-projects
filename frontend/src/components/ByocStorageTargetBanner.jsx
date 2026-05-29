import React, { useEffect, useState } from 'react';
import apiClient from '../api';
import '../styles/byoc-shared.css';

/**
 * Shows where Storage or Security files are stored (BYOC buckets or Zenith platform).
 */
export default function ByocStorageTargetBanner({ variant = 'storage' }) {
  const [targets, setTargets] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.get('/byoc/storage-targets');
        if (!cancelled) setTargets(res.data);
      } catch (e) {
        if (!cancelled) setError('Could not load storage destination.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error || !targets) return null;

  const isSecurity = variant === 'security';
  const info = isSecurity ? targets.security : targets.storage;
  const modeLabel = targets.mode === 'byoc' ? 'Your AWS account (BYOC)' : 'Zenith managed storage';

  return (
    <div className="byoc-target-banner" role="status">
      <strong>{isSecurity ? 'Secure vault destination' : 'Storage destination'}:</strong>{' '}
      <span className="byoc-target-mode">{modeLabel}</span>
      <ul className="byoc-target-list">
        <li>
          Bucket: <code>{info.bucket}</code> ({info.region})
        </li>
        <li>
          Path prefix: <code>{info.key_prefix}</code>
        </li>
        {isSecurity && info.replica_bucket && info.secure_dual_write && (
          <li>
            Replica: <code>{info.replica_bucket}</code> ({info.replica_region})
          </li>
        )}
      </ul>
      {targets.mode === 'byoc' && (
        <p className="byoc-target-hint">
          Create these buckets in AWS before connecting in Settings if you have not already.
        </p>
      )}
    </div>
  );
}
