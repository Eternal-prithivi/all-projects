import React from 'react';
import { formatGcpLocation, useGcpBuckets } from '../hooks/useGcpBuckets';
import BucketSelectorLoading from './BucketSelectorLoading.jsx';
import '../styles/bucket-selector.css';

const CHIP_THRESHOLD = 4;

/**
 * GCS bucket picker — location is fixed per bucket (shown read-only).
 */
export default function GcpBucketSelector({
  surface = 'storage',
  storageKeyPrefix = 'zenith.storage',
  selectedBucket,
  onBucketChange,
  enabled = true,
  compact = false,
  platformRegionSlug = null,
  reloadToken = 0,
}) {
  const {
    buckets,
    mode,
    platformMultiRegion,
    projectId,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectBucket,
  } = useGcpBuckets({
    surface,
    storageKeyPrefix,
    selectedBucket,
    onBucketChange,
    enabled,
    platformRegionSlug,
    reloadToken,
  });

  const isBusy = loading || refreshing;
  const useChips = buckets.length > 0 && buckets.length <= CHIP_THRESHOLD;

  return (
    <section
      className={`bucket-selector bucket-selector--gcp${compact ? ' bucket-selector--compact' : ''}`}
      aria-label="GCS bucket"
    >
      <div className="bucket-selector-top">
        <div className="bucket-selector-heading">
          <span className="bucket-selector-icon bucket-selector-icon--gcp" aria-hidden="true">
            <img src="/images/google-cloud_logo.png" alt="" width={20} height={20} />
          </span>
          <div>
            <h3 className="bucket-selector-title">Google Cloud Storage</h3>
            <p className="bucket-selector-subtitle">
              {mode === 'byoc'
                ? 'Your GCS buckets (BYOC)'
                : platformMultiRegion
                  ? 'Zenith platform — configured regions'
                  : 'Zenith platform GCS buckets'}
              {projectId ? ` · ${projectId}` : ''}
            </p>
          </div>
        </div>
        <div className="bucket-selector-top-actions">
          {!isBusy && buckets.length > 0 && (
            <span className="bucket-selector-stat">
              {buckets.length} bucket{buckets.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {selectedBucket && selectedMeta && (
        <div className="bucket-selector-context" role="status">
          <span className="bucket-selector-context-label">Viewing</span>
          <code className="bucket-selector-context-name" title={selectedBucket}>
            {selectedBucket}
          </code>
          {selectedMeta.location && (
            <span className="bucket-selector-context-region">
              {formatGcpLocation(selectedMeta.location)}
            </span>
          )}
          {selectedMeta.is_default && (
            <span className="bucket-selector-tag bucket-selector-tag--gold">Default</span>
          )}
        </div>
      )}

      {discoveryError && (
        <div className="bucket-selector-alert" role="alert">
          {discoveryError}
        </div>
      )}

      {isBusy ? (
        <BucketSelectorLoading label="Discovering GCS buckets…" />
      ) : buckets.length === 0 ? (
        <p className="bucket-selector-empty">
          {discoveryError || 'No GCS buckets found. Connect GCP in Settings or check server credentials.'}
        </p>
      ) : useChips ? (
        <div className="bucket-selector-chips" role="radiogroup" aria-label="GCS bucket">
          {buckets.map((b) => {
            const active = selectedBucket === b.name;
            return (
              <button
                key={b.name}
                type="button"
                role="radio"
                aria-checked={active}
                className={`bucket-selector-chip${active ? ' bucket-selector-chip--active' : ''}`}
                onClick={() => selectBucket(b)}
                title={b.name}
              >
                <span className="bucket-selector-chip-name">{b.name}</span>
                <span className="bucket-selector-chip-meta">
                  {b.platform_label && (
                    <span className="bucket-selector-chip-region">{b.platform_label}</span>
                  )}
                  {b.is_default && (
                    <span className="bucket-selector-tag bucket-selector-tag--gold">Default</span>
                  )}
                  {b.location && (
                    <span className="bucket-selector-chip-region">
                      {formatGcpLocation(b.location)}
                    </span>
                  )}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <select
          className="zenith-select bucket-selector-select"
          value={selectedBucket || ''}
          onChange={(e) => {
            const b = buckets.find((x) => x.name === e.target.value);
            if (b) selectBucket(b);
          }}
          aria-label="GCS bucket"
        >
          {!selectedBucket && <option value="">Select a GCS bucket…</option>}
          {buckets.map((b) => (
            <option key={b.name} value={b.name}>
              {b.name}
              {b.location ? ` · ${formatGcpLocation(b.location)}` : ''}
              {b.is_default ? ' · Default' : ''}
            </option>
          ))}
        </select>
      )}

      <p className="bucket-selector-hint">
        Bucket location is set when the bucket is created — choose a different bucket to change region.
      </p>
    </section>
  );
}
