import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getAwsBuckets, refreshAwsBuckets } from '../api';
import { minLoadingDelay } from '../utils/minLoadingDelay';

export const REGION_LABELS = {
  'ap-south-1': 'Mumbai',
  'us-east-1': 'Virginia',
  'us-west-2': 'Oregon',
  'eu-west-1': 'Ireland',
  'af-south-1': 'Cape Town',
};

export function platformRegionsFromBuckets(buckets = []) {
  const map = new Map();
  for (const b of buckets) {
    if (b.platform_slug) {
      map.set(b.platform_slug, b.platform_label || b.platform_slug);
    }
  }
  return Array.from(map, ([slug, label]) => ({ slug, label }));
}

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
  platformRegionSlug = null,
  reloadToken = 0,
}) {
  const [buckets, setBuckets] = useState([]);
  const [mode, setMode] = useState('platform');
  const [platformMultiRegion, setPlatformMultiRegion] = useState(false);
  const [defaultPlatformSlug, setDefaultPlatformSlug] = useState('');
  const [supportedRegions, setSupportedRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [discoveryError, setDiscoveryError] = useState(null);
  const didAutoSelect = useRef(false);
  const didInitialLoad = useRef(false);
  const selectedBucketRef = useRef(selectedBucket);
  const onBucketChangeRef = useRef(onBucketChange);
  const onRegionChangeRef = useRef(onRegionChange);
  const onBucketsLoadedRef = useRef(onBucketsLoaded);
  selectedBucketRef.current = selectedBucket;
  onBucketChangeRef.current = onBucketChange;
  onRegionChangeRef.current = onRegionChange;
  onBucketsLoadedRef.current = onBucketsLoaded;

  const loadBuckets = useCallback(
    async (forceRefresh = false) => {
      const startedAt = Date.now();
      setLoading(true);
      try {
        // Platform multi-region catalog: always load all buckets; filter by platform pill client-side.
        // BYOC only: pass AWS region code to narrow live discovery.
        const regionParam =
          mode === 'byoc' &&
          !platformMultiRegion &&
          selectedRegion &&
          selectedRegion !== 'all'
            ? selectedRegion
            : undefined;
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
          if (list.length && onRegionChangeRef.current) {
            try {
              sessionStorage.setItem(`${storageKeyPrefix}.region`, 'all');
            } catch {
              /* ignore */
            }
            onRegionChangeRef.current('all');
          }
        }

        setBuckets(list);
        const regions = platformRegionsFromBuckets(list);
        onBucketsLoadedRef.current?.(list, {
          platformMultiRegion: Boolean(data.platform_multi_region),
          defaultPlatformSlug: data.default_platform_slug || regions[0]?.slug || '',
          platformRegions: regions,
          mode: data.mode || 'platform',
        });
        setMode(data.mode || 'platform');
        setPlatformMultiRegion(Boolean(data.platform_multi_region));
        setDefaultPlatformSlug(data.default_platform_slug || regions[0]?.slug || '');
        setSupportedRegions(data.supported_regions || []);
        setDiscoveryError(data.discovery_error || null);

        if (list.length && !selectedBucketRef.current && !didAutoSelect.current) {
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
          onBucketChangeRef.current?.(pick.name, pick.region);
        }
      } catch (e) {
        setDiscoveryError(e.message || 'Could not load buckets.');
        setBuckets([]);
      } finally {
        await minLoadingDelay(startedAt);
        setLoading(false);
        setRefreshing(false);
      }
    },
    [surface, selectedRegion, storageKeyPrefix, mode, platformMultiRegion]
  );

  useEffect(() => {
    if (didInitialLoad.current) {
      setRefreshing(true);
    }
    didInitialLoad.current = true;
    loadBuckets(false);
  }, [loadBuckets, reloadToken]);

  const selectBucket = useCallback(
    (b) => {
      try {
        sessionStorage.setItem(`${storageKeyPrefix}.bucket`, b.name);
        if (b.region) sessionStorage.setItem(`${storageKeyPrefix}.region`, b.region);
      } catch {
        /* ignore */
      }
      onBucketChangeRef.current?.(b.name, b.region || selectedRegion);
    },
    [storageKeyPrefix, selectedRegion]
  );

  const displayBuckets = useMemo(() => {
    if (!platformMultiRegion || !platformRegionSlug) return buckets;
    return buckets.filter((b) => b.platform_slug === platformRegionSlug);
  }, [buckets, platformMultiRegion, platformRegionSlug]);

  useEffect(() => {
    if (!platformMultiRegion || !platformRegionSlug || !buckets.length) return;
    const match = buckets.find((b) => b.platform_slug === platformRegionSlug);
    if (match && selectedBucketRef.current !== match.name) {
      selectBucket(match);
    }
  }, [platformMultiRegion, platformRegionSlug, buckets, selectBucket]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await loadBuckets(true);
  }, [loadBuckets]);

  const selectedMeta = displayBuckets.find((b) => b.name === selectedBucket);

  return {
    buckets: displayBuckets,
    allBuckets: buckets,
    mode,
    platformMultiRegion,
    defaultPlatformSlug,
    platformRegions: platformRegionsFromBuckets(buckets),
    supportedRegions,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectBucket,
    refresh,
    showRegionFilter: mode === 'byoc' && supportedRegions.length > 0,
    staticPlatformCatalog: mode === 'platform',
  };
}
