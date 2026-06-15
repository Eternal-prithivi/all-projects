import React from 'react';
import { IconRefresh } from '../dashboard/Icons.jsx';

/**
 * Gold compact refresh — same style as the dashboard Cost Overview card.
 * Used in page headers, chart panels, and inline card actions.
 */
export default function ZenithRefreshButton({
  onClick,
  busy = false,
  disabled = false,
  label = 'Refresh',
  busyLabel = 'Refreshing…',
  className = '',
  title,
}) {
  if (typeof onClick !== 'function') return null;

  const aria = busy ? busyLabel : label;

  return (
    <button
      type="button"
      className={`zenith-refresh-btn ${className}`.trim()}
      onClick={onClick}
      disabled={disabled || busy}
      aria-label={aria}
      title={title ?? aria}
    >
      <IconRefresh
        className={`zenith-refresh-btn__icon${busy ? ' is-spinning' : ''}`}
        aria-hidden="true"
      />
      <span>{busy ? busyLabel : label}</span>
    </button>
  );
}
