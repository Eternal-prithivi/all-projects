import React from 'react';
import PlatformRegionPills from './PlatformRegionPills';
import '../styles/storage-region-scope.css';

/**
 * Prominent region context for the file list — placed directly above "Your files"
 * so users always know which geographic scope they are viewing.
 */
export default function StorageRegionScopeBar({
  platformRegions = [],
  selectedSlug,
  onSelect,
  onReset,
  accountDefaultRegion = null,
  isSessionOverride = false,
  fileCount = 0,
  filteredCount = null,
  cloudProvider = 'ALL',
}) {
  if (!platformRegions.length || platformRegions.length < 2) return null;

  const active = platformRegions.find((r) => r.slug === selectedSlug);
  const activeLabel = active?.label || selectedSlug || 'Unknown';
  const defaultRegion = platformRegions.find((r) => r.slug === accountDefaultRegion);
  const defaultLabel = defaultRegion?.label || accountDefaultRegion;

  const countInView =
    filteredCount != null && cloudProvider !== 'ALL' ? filteredCount : fileCount;
  const countLabel =
    cloudProvider !== 'ALL'
      ? `${countInView} ${cloudProvider} file${countInView === 1 ? '' : 's'} in ${activeLabel}`
      : `${fileCount} file${fileCount === 1 ? '' : 's'} in ${activeLabel}`;

  return (
    <section
      className="storage-region-scope"
      aria-label="Storage region scope"
    >
      <div className="storage-region-scope__main">
        <div className="storage-region-scope__icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
            <path
              d="M3 12h18M12 3c2.5 2.8 4 6.2 4 9s-1.5 6.2-4 9M12 3c-2.5 2.8-4 6.2-4 9s1.5 6.2 4 9"
              stroke="currentColor"
              strokeWidth="1.5"
            />
          </svg>
        </div>
        <div className="storage-region-scope__copy">
          <p className="storage-region-scope__eyebrow">Active storage region</p>
          <div className="storage-region-scope__title-row">
            <h4 className="storage-region-scope__title">{activeLabel}</h4>
            <span className="storage-region-scope__count" role="status">
              {countLabel}
            </span>
          </div>
          <p className="storage-region-scope__hint">
            Upload, sync, and delete apply to this region only. Each region keeps its
            own copy of your data across AWS, GCP, and Azure.
          </p>
        </div>
      </div>

      <div className="storage-region-scope__controls">
        <PlatformRegionPills
          regions={platformRegions}
          selectedSlug={selectedSlug}
          onSelect={onSelect}
          id="storage-file-region"
          rowLabel="Switch region"
        />
        {isSessionOverride && defaultLabel && (
          <p className="storage-region-scope__override" role="status">
            Temporary view — account default is{' '}
            <strong>{defaultLabel}</strong>
            {typeof onReset === 'function' && (
              <button
                type="button"
                className="storage-region-scope__reset"
                onClick={onReset}
              >
                Use default
              </button>
            )}
          </p>
        )}
      </div>
    </section>
  );
}

/** Resolve friendly platform label for a file row. */
export function platformLabelForSlug(slug, platformRegions = []) {
  if (!slug) return null;
  const match = platformRegions.find((r) => r.slug === slug);
  return match?.label || slug;
}
