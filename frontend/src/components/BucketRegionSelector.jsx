import React, { useMemo, useState } from 'react';
import {
  formatRegionLabel,
  REGION_LABELS,
  useAwsBuckets,
} from '../hooks/useAwsBuckets';
import '../styles/bucket-selector.css';

const CHIP_THRESHOLD = 4;

function bucketLabel(b) {
  const tags = [];
  if (b.is_default) tags.push('Default');
  if (b.is_replica) tags.push('Replica');
  const region = b.region ? formatRegionLabel(b.region) : '';
  if (region) tags.push(region);
  return tags.length ? `${b.name} · ${tags.join(' · ')}` : b.name;
}

/**
 * Inline S3 destination picker (region pills + bucket chips or searchable list).
 * Replaces the sidebar pattern with a cloud-console-style context bar.
 */
export default function BucketRegionSelector({
  surface = 'storage',
  storageKeyPrefix = 'zenith.storage',
  selectedBucket,
  selectedRegion = 'all',
  onBucketChange,
  onRegionChange,
  onBucketsLoaded,
}) {
  const [search, setSearch] = useState('');

  const {
    buckets,
    mode,
    supportedRegions,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectBucket,
    refresh,
    showRegionFilter,
  } = useAwsBuckets({
    surface,
    storageKeyPrefix,
    selectedBucket,
    selectedRegion,
    onBucketChange,
    onRegionChange,
    onBucketsLoaded,
  });

  const handleRegionClick = (value) => {
    try {
      sessionStorage.setItem(`${storageKeyPrefix}.region`, value);
    } catch {
      /* ignore */
    }
    onRegionChange(value);
  };

  const filteredBuckets = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return buckets;
    return buckets.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        (b.region && b.region.toLowerCase().includes(q))
    );
  }, [buckets, search]);

  const useChips = buckets.length > 0 && buckets.length <= CHIP_THRESHOLD;
  const title = surface === 'security' ? 'Secure vault' : 'General storage';
  const subtitle =
    mode === 'byoc'
      ? surface === 'security'
        ? 'Secure and replica buckets only — not shown on the Storage page'
        : 'Standard buckets only — secure vault buckets appear under Security'
      : surface === 'security'
        ? 'Zenith secure vault and replica'
        : 'Zenith-managed object storage';

  return (
    <section
      className={`bucket-selector bucket-selector--${surface}`}
      aria-label="S3 bucket and region"
    >
      <div className="bucket-selector-top">
        <div className="bucket-selector-heading">
          <span className="bucket-selector-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 7h16v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7z" />
              <path d="M4 7l2-4h12l2 4" />
            </svg>
          </span>
          <div>
            <h3 className="bucket-selector-title">{title}</h3>
            <p className="bucket-selector-subtitle">{subtitle}</p>
          </div>
        </div>
        <div className="bucket-selector-top-actions">
          {!loading && buckets.length > 0 && (
            <span className="bucket-selector-stat">
              {buckets.length} bucket{buckets.length !== 1 ? 's' : ''}
            </span>
          )}
          {mode === 'byoc' && (
            <button
              type="button"
              className="bucket-selector-refresh"
              onClick={refresh}
              disabled={refreshing || loading}
              aria-label="Refresh buckets from AWS"
            >
              <svg
                className={refreshing ? 'bucket-selector-spin' : ''}
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                <path d="M21 3v6h-6" />
              </svg>
              Refresh
            </button>
          )}
        </div>
      </div>

      {selectedBucket && selectedMeta && (
        <div className="bucket-selector-context" role="status">
          <span className="bucket-selector-context-label">Viewing</span>
          <code className="bucket-selector-context-name" title={selectedBucket}>
            {selectedBucket}
          </code>
          {selectedMeta.region && (
            <span className="bucket-selector-context-region">
              {formatRegionLabel(selectedMeta.region)}
            </span>
          )}
          {selectedMeta.is_default && (
            <span className="bucket-selector-tag bucket-selector-tag--gold">Default</span>
          )}
          {selectedMeta.is_replica && (
            <span className="bucket-selector-tag">Replica</span>
          )}
        </div>
      )}

      {discoveryError && (
        <div className="bucket-selector-alert" role="alert">
          {discoveryError}
        </div>
      )}

      {loading ? (
        <div className="bucket-selector-loading" aria-busy="true">
          <span className="bucket-selector-loading-bar" />
          <span className="bucket-selector-loading-text">Discovering buckets…</span>
        </div>
      ) : (
        <>
          {showRegionFilter && (
            <div className="bucket-selector-row">
              <span className="bucket-selector-row-label" id={`region-label-${surface}`}>
                Region
              </span>
              <div
                className="bucket-selector-pills"
                role="group"
                aria-labelledby={`region-label-${surface}`}
              >
                <button
                  type="button"
                  className={`bucket-selector-pill${
                    (!selectedRegion || selectedRegion === 'all') ? ' bucket-selector-pill--active' : ''
                  }`}
                  onClick={() => handleRegionClick('all')}
                >
                  All
                </button>
                {supportedRegions.map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={`bucket-selector-pill${
                      selectedRegion === r ? ' bucket-selector-pill--active' : ''
                    }`}
                    onClick={() => handleRegionClick(r)}
                  >
                    {REGION_LABELS[r] || r}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="bucket-selector-row bucket-selector-row--bucket">
            <span className="bucket-selector-row-label" id={`bucket-label-${surface}`}>
              Bucket
            </span>
            {buckets.length === 0 ? (
              <div className="bucket-selector-empty-block">
                <p className="bucket-selector-empty">
                  {discoveryError ||
                    (surface === 'storage'
                      ? 'No general storage buckets found. Connect AWS BYOC with a storage bucket, or use the Security page for vault buckets.'
                      : 'No secure vault buckets found. Run BYOC setup or open the Security upload wizard.')}
                </p>
                {selectedRegion && selectedRegion !== 'all' && (
                  <button
                    type="button"
                    className="bucket-selector-clear-region"
                    onClick={() => handleRegionClick('all')}
                  >
                    Show all regions
                  </button>
                )}
                {mode === 'byoc' && (
                  <button
                    type="button"
                    className="bucket-selector-clear-region"
                    onClick={refresh}
                    disabled={refreshing}
                  >
                    Refresh from AWS
                  </button>
                )}
              </div>
            ) : useChips ? (
              <div
                className="bucket-selector-chips"
                role="radiogroup"
                aria-labelledby={`bucket-label-${surface}`}
              >
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
                        {b.is_default && <span className="bucket-selector-tag bucket-selector-tag--gold">Default</span>}
                        {b.is_replica && <span className="bucket-selector-tag">Replica</span>}
                        {b.region && (
                          <span className="bucket-selector-chip-region">
                            {formatRegionLabel(b.region)}
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="bucket-selector-picker" aria-labelledby={`bucket-label-${surface}`}>
                {buckets.length > 5 && (
                  <input
                    type="search"
                    className="bucket-selector-search"
                    placeholder="Search buckets…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    aria-label="Search buckets"
                  />
                )}
                <select
                  className="zenith-select bucket-selector-select"
                  value={selectedBucket || ''}
                  onChange={(e) => {
                    const b = buckets.find((x) => x.name === e.target.value);
                    if (b) selectBucket(b);
                  }}
                >
                  {!selectedBucket && <option value="">Select a bucket…</option>}
                  {filteredBuckets.map((b) => (
                    <option key={b.name} value={b.name}>
                      {bucketLabel(b)}
                    </option>
                  ))}
                </select>
                {search && filteredBuckets.length === 0 && (
                  <p className="bucket-selector-empty">No buckets match &quot;{search}&quot;.</p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
