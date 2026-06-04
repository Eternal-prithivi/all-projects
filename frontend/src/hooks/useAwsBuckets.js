import { useCallback, useEffect, useRef, useState } from 'react';
import { getAwsBuckets, refreshAwsBuckets } from '../api';

export const REGION_LABELS = {
  'ap-south-1': 'Mumbai',
  'us-east-1': 'Virginia',
  'us-west-2': 'Oregon',
  'eu-west-1': 'Ireland',
};

export function formatRegionLabel(code) {
  if (!code || code === 'all') return 'All regions';
  return REGION_LABELS[code] || code;
}

/**
 * Load and filter AWS buckets for Storage or Security surfaces.
 */
export function useAwsBuckets({
  surface = 'storage',
  storageKeyPrefix = 'zenith.storage',
  selectedBucket,
  selectedRegion,
  onBucketChange,
  onRegionChange,
  onBucketsLoaded,
}) {
  const [buckets, setBuckets] = useState([]);
  const [mode, setMode] = useState('platform');
  const [supportedRegions, setSupportedRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [discoveryError, setDiscoveryError] = useState(null);
  const didAutoSelect = useRef(false);

  const loadBuckets = useCallback(
    async (forceRefresh = false) => {
      setLoading(true);
      try {
        const regionParam =
          selectedRegion && selectedRegion !== 'all' ? selectedRegion : undefined;
        let data = forceRefresh
          ? await refreshAwsBuckets(surface, { region: regionParam })
          : await getAwsBuckets(surface, { region: regionParam });
        let list = data.buckets || [];

        // Stale session region (e.g. from BYOC) with platform mode → retry without filter
        if (
          !list.length &&
          regionParam &&
          (data.mode === 'platform' || data.discovery_error)
        ) {
          data = forceRefresh
            ? await refreshAwsBuckets(surface, {})
            : await getAwsBuckets(surface, {});
          list = data.buckets || [];
          if (list.length && onRegionChange) {
            try {
              sessionStorage.setItem(`${storageKeyPrefix}.region`, 'all');
            } catch {
              /* ignore */
            }
            onRegionChange('all');
          }
        }

        setBuckets(list);
        onBucketsLoaded?.(list);
        setMode(data.mode || 'platform');
        setSupportedRegions(data.supported_regions || []);
        setDiscoveryError(data.discovery_error || null);

        if (list.length && !selectedBucket && !didAutoSelect.current) {
          let stored = null;
          try {
            stored = sessionStorage.getItem(`${storageKeyPrefix}.bucket`);
          } catch {
            /* ignore */
          }
          const pick =
            list.find((b) => b.name === stored) ||
            list.find((b) => b.is_default) ||
            list[0];
          didAutoSelect.current = true;
          onBucketChange(pick.name, pick.region);
        }
      } catch (e) {
        setDiscoveryError(e.message || 'Could not load buckets.');
        setBuckets([]);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [
      surface,
      selectedRegion,
      selectedBucket,
      onBucketChange,
      onRegionChange,
      storageKeyPrefix,
      onBucketsLoaded,
    ]
  );

  useEffect(() => {
    loadBuckets(false);
  }, [loadBuckets, selectedRegion]);

  const selectBucket = useCallback(
    (b) => {
      try {
        sessionStorage.setItem(`${storageKeyPrefix}.bucket`, b.name);
        if (b.region) sessionStorage.setItem(`${storageKeyPrefix}.region`, b.region);
      } catch {
        /* ignore */
      }
      onBucketChange(b.name, b.region || selectedRegion);
    },
    [storageKeyPrefix, onBucketChange, selectedRegion]
  );

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await loadBuckets(true);
  }, [loadBuckets]);

  const selectedMeta = buckets.find((b) => b.name === selectedBucket);

  return {
    buckets,
    mode,
    supportedRegions,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectBucket,
    refresh,
    showRegionFilter: mode === 'byoc' && supportedRegions.length > 0,
  };
}
