/* eslint-disable react-refresh/only-export-components */
import React from 'react';
import ZenithRefreshButton from './ui/ZenithRefreshButton.jsx';
import '../styles/cloud-provider-toolbar.css';

export const CLOUD_PROVIDER_OPTIONS = [
  { value: 'ALL', label: 'All' },
  { value: 'AWS', label: 'AWS' },
  { value: 'GCP', label: 'GCP' },
  { value: 'Azure', label: 'Azure' },
];

/** @deprecated Use buildCloudProviderOptions from useCloudAvailability.js */
export const LEGACY_CLOUD_PROVIDER_OPTIONS = CLOUD_PROVIDER_OPTIONS;

/** Client-side filter for file rows that include a `csp` field (defaults to AWS). */
export function filterFilesByCloudProvider(files, provider) {
  if (!provider || provider === 'ALL') {
    return files;
  }
  return files.filter((file) => (file.csp || 'AWS') === provider);
}

/**
 * Toolbar: provider dropdown + action button (sync). Stacks on narrow screens.
 */
export default function CloudProviderToolbar({
  provider,
  onProviderChange,
  onAction,
  actionLabel,
  actionDisabled = false,
  actionBusy = false,
  onRefresh,
  refreshBusy = false,
  refreshDisabled = false,
  refreshLabel = 'Refresh',
  actionClassName = 'action-btn',
  selectAriaLabel = 'Cloud provider',
  className = '',
  /** When set, only these providers (+ optional ALL) appear in the dropdown */
  providerOptions = CLOUD_PROVIDER_OPTIONS,
}) {
  const options =
    providerOptions && providerOptions.length > 0
      ? providerOptions
      : CLOUD_PROVIDER_OPTIONS;

  return (
    <div className={`cloud-provider-toolbar ${className}`.trim()}>
      <select
        className="zenith-select cloud-provider-toolbar__select"
        value={provider}
        onChange={(e) => onProviderChange(e.target.value)}
        aria-label={selectAriaLabel}
        disabled={options.length <= 1 && options[0]?.value !== 'ALL'}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {typeof onRefresh === 'function' && (
        <ZenithRefreshButton
          onClick={onRefresh}
          busy={refreshBusy}
          disabled={refreshDisabled}
          label={refreshLabel}
          className="cloud-provider-toolbar__refresh"
        />
      )}
      {typeof onAction === 'function' && (
        <button
          type="button"
          className={`${actionClassName} cloud-provider-toolbar__action`.trim()}
          onClick={onAction}
          disabled={actionDisabled || actionBusy}
        >
          {actionBusy ? 'Syncing…' : actionLabel}
        </button>
      )}
    </div>
  );
}
