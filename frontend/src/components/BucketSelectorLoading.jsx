import React from 'react';
import IndeterminateProgressBar from './IndeterminateProgressBar.jsx';

/**
 * Shared gold loading row for AWS / GCP / Azure bucket selectors.
 */
export default function BucketSelectorLoading({ label = 'Loading destinations…' }) {
  return (
    <div className="bucket-selector-loading" aria-busy="true">
      <IndeterminateProgressBar variant="gold" label={label} className="bucket-selector-loading__bar" />
      <span className="bucket-selector-loading-text">{label}</span>
    </div>
  );
}
