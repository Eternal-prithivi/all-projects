import React from 'react';
import { useAzureContainers } from '../hooks/useAzureContainers';
import BucketSelectorLoading from './BucketSelectorLoading.jsx';
import '../styles/bucket-selector.css';

const CHIP_THRESHOLD = 4;

/**
 * Azure Blob container picker — region is fixed at the storage account level.
 */
export default function AzureContainerSelector({
  surface = 'storage',
  storageKeyPrefix = 'zenith.storage',
  selectedContainer,
  onContainerChange,
  enabled = true,
  compact = false,
  platformRegionSlug = null,
  reloadToken = 0,
}) {
  const {
    containers,
    mode,
    platformMultiRegion,
    accountName,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectContainer,
  } = useAzureContainers({
    surface,
    storageKeyPrefix,
    selectedContainer,
    onContainerChange,
    enabled,
    platformRegionSlug,
    reloadToken,
  });

  const isBusy = loading || refreshing;
  const useChips = containers.length > 0 && containers.length <= CHIP_THRESHOLD;

  return (
    <section
      className={`bucket-selector bucket-selector--azure${compact ? ' bucket-selector--compact' : ''}`}
      aria-label="Azure Blob container"
    >
      <div className="bucket-selector-top">
        <div className="bucket-selector-heading">
          <span className="bucket-selector-icon bucket-selector-icon--azure" aria-hidden="true">
            <img src="/images/Microsoft_Azure.png" alt="" width={20} height={20} />
          </span>
          <div>
            <h3 className="bucket-selector-title">Azure Blob Storage</h3>
            <p className="bucket-selector-subtitle">
              {mode === 'byoc'
                ? 'Your Blob containers (BYOC)'
                : platformMultiRegion
                  ? 'Zenith platform — configured regions'
                  : 'Zenith platform Blob containers'}
              {accountName ? ` · ${accountName}` : ''}
            </p>
          </div>
        </div>
        <div className="bucket-selector-top-actions">
          {!isBusy && containers.length > 0 && (
            <span className="bucket-selector-stat">
              {containers.length} container{containers.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {selectedContainer && selectedMeta && (
        <div className="bucket-selector-context" role="status">
          <span className="bucket-selector-context-label">Viewing</span>
          <code className="bucket-selector-context-name" title={selectedContainer}>
            {selectedContainer}
          </code>
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
        <BucketSelectorLoading label="Discovering Azure containers…" />
      ) : containers.length === 0 ? (
        <p className="bucket-selector-empty">
          {discoveryError || 'No Blob containers found. Connect Azure in Settings or check server credentials.'}
        </p>
      ) : useChips ? (
        <div className="bucket-selector-chips" role="radiogroup" aria-label="Azure container">
          {containers.map((c) => {
            const active = selectedContainer === c.name;
            return (
              <button
                key={c.name}
                type="button"
                role="radio"
                aria-checked={active}
                className={`bucket-selector-chip${active ? ' bucket-selector-chip--active' : ''}`}
                onClick={() => selectContainer(c)}
                title={c.name}
              >
                <span className="bucket-selector-chip-name">{c.name}</span>
                <span className="bucket-selector-chip-meta">
                  {c.platform_label && (
                    <span className="bucket-selector-chip-region">{c.platform_label}</span>
                  )}
                  {c.is_default && (
                    <span className="bucket-selector-tag bucket-selector-tag--gold">Default</span>
                  )}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <select
          className="zenith-select bucket-selector-select"
          value={selectedContainer || ''}
          onChange={(e) => {
            const c = containers.find((x) => x.name === e.target.value);
            if (c) selectContainer(c);
          }}
          aria-label="Azure container"
        >
          {!selectedContainer && <option value="">Select a container…</option>}
          {containers.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
              {c.is_default ? ' · Default' : ''}
            </option>
          ))}
        </select>
      )}

      <p className="bucket-selector-hint">
        Region is tied to your storage account — pick another container or account to change region.
      </p>
    </section>
  );
}
