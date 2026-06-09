import React from 'react';

/**
 * Cloud-console style page refresh — reloads current page data only.
 */
export default function PageRefreshButton({
  onClick,
  busy = false,
  disabled = false,
  label = 'Refresh',
  busyLabel = 'Refreshing…',
  className = '',
}) {
  if (typeof onClick !== 'function') return null;

  return (
    <button
      type="button"
      className={`page-refresh-btn ${className}`.trim()}
      onClick={onClick}
      disabled={disabled || busy}
      aria-label={busy ? busyLabel : label}
      title={busy ? busyLabel : label}
    >
      <svg
        className={busy ? 'page-refresh-btn__icon--spin' : ''}
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path d="M21 12a9 9 0 1 1-2.64-6.36" />
        <path d="M21 3v6h-6" />
      </svg>
      <span>{busy ? busyLabel : label}</span>
    </button>
  );
}
