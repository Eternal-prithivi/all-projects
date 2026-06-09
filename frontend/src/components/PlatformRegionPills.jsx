import React from 'react';
import '../styles/bucket-selector.css';

/**
 * Canonical platform region pills (asia, us, europe, africa) — shared across CSP selectors.
 */
export default function PlatformRegionPills({
  regions = [],
  selectedSlug,
  onSelect,
  id = 'platform-region',
  hideLabel = false,
  rowLabel = 'Region',
}) {
  if (!regions.length) return null;

  return (
    <div className="bucket-selector-row platform-region-row">
      {!hideLabel && (
        <span className="bucket-selector-row-label" id={id}>
          {rowLabel}
        </span>
      )}
      <div
        className="bucket-selector-pills"
        role="group"
        aria-labelledby={hideLabel ? undefined : id}
        aria-label={hideLabel ? 'Platform region' : undefined}
      >
        {regions.map((r) => (
          <button
            key={r.slug}
            type="button"
            className={`bucket-selector-pill${
              selectedSlug === r.slug ? ' bucket-selector-pill--active' : ''
            }`}
            onClick={() => onSelect(r.slug)}
          >
            {r.label || r.slug}
          </button>
        ))}
      </div>
    </div>
  );
}
