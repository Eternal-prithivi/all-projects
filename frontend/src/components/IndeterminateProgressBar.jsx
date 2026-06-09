import React from 'react';
import '../styles/indeterminate-progress.css';

/**
 * GCP-style sliding horizontal progress bar for loading states.
 */
export default function IndeterminateProgressBar({
  className = '',
  variant = 'default',
  label = null,
}) {
  return (
    <div
      className={`indeterminate-progress indeterminate-progress--${variant} ${className}`.trim()}
      role="progressbar"
      aria-label={label || 'In progress'}
      aria-valuetext="In progress"
    >
      <div className="indeterminate-progress__track">
        <div className="indeterminate-progress__bar" />
      </div>
    </div>
  );
}
