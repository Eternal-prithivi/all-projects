import React from 'react';
import ZenithRefreshButton from './ZenithRefreshButton.jsx';

/**
 * Page-header refresh — delegates to the shared gold dashboard refresh style.
 */
export default function PageRefreshButton({
  onClick,
  busy = false,
  disabled = false,
  label = 'Refresh',
  busyLabel = 'Refreshing…',
  className = '',
}) {
  return (
    <ZenithRefreshButton
      onClick={onClick}
      busy={busy}
      disabled={disabled}
      label={label}
      busyLabel={busyLabel}
      className={className}
    />
  );
}
