import React from 'react';
import BucketRegionSelector from './BucketRegionSelector';
import GcpBucketSelector from './GcpBucketSelector';
import AzureContainerSelector from './AzureContainerSelector';
import PlatformRegionPills from './PlatformRegionPills';
import '../styles/bucket-selector.css';

function showProvider(activeCsp, provider) {
  return activeCsp === 'ALL' || activeCsp === provider;
}

/**
 * Multi-cloud storage destination panel — filters by active CSP toolbar selection.
 */
export default function CloudDestinationPanel({
  surface = 'storage',
  storageKeyPrefix = 'zenith.storage',
  activeCsp = 'ALL',
  storageProviders = [],
  selectedBucket,
  selectedRegion = 'all',
  onBucketChange,
  onRegionChange,
  onBucketsLoaded,
  selectedGcpBucket,
  onGcpBucketChange,
  selectedAzureContainer,
  onAzureContainerChange,
  platformRegionSlug = null,
  onPlatformRegionChange,
  onResetPlatformRegion,
  accountDefaultRegion = null,
  isRegionSessionOverride = false,
  platformMultiRegion = false,
  platformRegions = [],
  hidePlatformRegionSelector = false,
  reloadToken = 0,
}) {
  const hasAws = storageProviders.includes('AWS');
  const hasGcp = storageProviders.includes('GCP');
  const hasAzure = storageProviders.includes('Azure');
  const multiSection =
    (activeCsp === 'ALL' &&
      [hasAws, hasGcp, hasAzure].filter(Boolean).length > 1) ||
    false;

  const showPlatformRegions =
    !hidePlatformRegionSelector &&
    platformMultiRegion &&
    platformRegions.length > 1 &&
    typeof onPlatformRegionChange === 'function';
  const activeRegionLabel = platformRegions.find((r) => r.slug === platformRegionSlug)?.label;
  const accountDefaultLabel = platformRegions.find((r) => r.slug === accountDefaultRegion)?.label;

  return (
    <div className={`cloud-destination-panel${multiSection ? ' cloud-destination-panel--stacked' : ''}`}>
      {showPlatformRegions && (
        <div className="platform-region-panel">
          <PlatformRegionPills
            regions={platformRegions}
            selectedSlug={platformRegionSlug}
            onSelect={onPlatformRegionChange}
          />
          {activeRegionLabel && (
            <p className="platform-region-active" role="status">
              {isRegionSessionOverride ? (
                <>
                  Session override: <strong>{activeRegionLabel}</strong>
                  {accountDefaultLabel && (
                    <>
                      {' '}
                      (account default: {accountDefaultLabel})
                    </>
                  )}
                  {typeof onResetPlatformRegion === 'function' && (
                    <button
                      type="button"
                      className="platform-region-reset"
                      onClick={onResetPlatformRegion}
                    >
                      Reset to account default
                    </button>
                  )}
                </>
              ) : (
                <>
                  Account default region: <strong>{activeRegionLabel}</strong>
                  {' — '}
                  pick another pill to override for this session only.
                </>
              )}
            </p>
          )}
        </div>
      )}
      {hasAws && showProvider(activeCsp, 'AWS') && (
        <BucketRegionSelector
          surface={surface}
          storageKeyPrefix={storageKeyPrefix}
          selectedBucket={selectedBucket}
          selectedRegion={selectedRegion}
          onBucketChange={onBucketChange}
          onRegionChange={onRegionChange}
          onBucketsLoaded={onBucketsLoaded}
          platformRegionSlug={platformRegionSlug}
          reloadToken={reloadToken}
        />
      )}
      {hasGcp && showProvider(activeCsp, 'GCP') && (
        <GcpBucketSelector
          storageKeyPrefix={storageKeyPrefix}
          selectedBucket={selectedGcpBucket}
          onBucketChange={onGcpBucketChange}
          enabled={hasGcp}
          compact={multiSection}
          platformRegionSlug={platformRegionSlug}
          reloadToken={reloadToken}
        />
      )}
      {hasAzure && showProvider(activeCsp, 'Azure') && (
        <AzureContainerSelector
          storageKeyPrefix={storageKeyPrefix}
          selectedContainer={selectedAzureContainer}
          onContainerChange={onAzureContainerChange}
          enabled={hasAzure}
          compact={multiSection}
          platformRegionSlug={platformRegionSlug}
          reloadToken={reloadToken}
        />
      )}
    </div>
  );
}
