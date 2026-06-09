import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getGcpBuckets } from '../api';
import { minLoadingDelay } from '../utils/minLoadingDelay';
import { platformRegionsFromBuckets } from './useAwsBuckets';

export function formatGcpLocation(code) {
  if (!code) return '';
  return code
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Load GCS buckets for Storage destination picker.
 */
export function useGcpBuckets({
  storageKeyPrefix = 'zenith.storage',
  selectedBucket,
  onBucketChange,
  enabled = true,
  platformRegionSlug = null,
  reloadToken = 0,
}) {
  const [buckets, setBuckets] = useState([]);
  const [mode, setMode] = useState('platform');
  const [platformMultiRegion, setPlatformMultiRegion] = useState(false);
  const [projectId, setProjectId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [discoveryError, setDiscoveryError] = useState(null);
  const didAutoSelect = useRef(false);
  const didInitialLoad = useRef(false);
  const selectedBucketRef = useRef(selectedBucket);
  const onBucketChangeRef = useRef(onBucketChange);
  selectedBucketRef.current = selectedBucket;
  onBucketChangeRef.current = onBucketChange;

  const loadBuckets = useCallback(async () => {
    if (!enabled) {
      setBuckets([]);
      setLoading(false);
      return;
    }
    const startedAt = Date.now();
    setLoading(true);
    try {
      const data = await getGcpBuckets();
      const list = data.buckets || [];
      setBuckets(list);
      setMode(data.mode || 'platform');
      setPlatformMultiRegion(Boolean(data.platform_multi_region));
      setProjectId(data.project_id || null);
      setDiscoveryError(data.error || null);

      if (list.length && !selectedBucketRef.current && !didAutoSelect.current) {
        let stored = null;
        try {
          stored = sessionStorage.getItem(`${storageKeyPrefix}.gcp.bucket`);
        } catch {
          /* ignore */
        }
        const pick =
          list.find((b) => b.name === stored) ||
          list.find((b) => b.is_default) ||
          list[0];
        didAutoSelect.current = true;
        onBucketChangeRef.current?.(pick.name, pick.location || null);
      }
    } catch (e) {
      const msg = e?.detail || e?.message || 'Could not load GCS buckets.';
      setDiscoveryError(typeof msg === 'string' ? msg : 'Could not load GCS buckets.');
      setBuckets([]);
    } finally {
      await minLoadingDelay(startedAt);
      setLoading(false);
      setRefreshing(false);
    }
  }, [enabled, storageKeyPrefix, reloadToken]);

  useEffect(() => {
    if (!enabled) return;
    if (didInitialLoad.current) {
      setRefreshing(true);
    }
    didInitialLoad.current = true;
    loadBuckets();
  }, [loadBuckets, enabled]);

  const selectBucket = useCallback(
    (b) => {
      try {
        sessionStorage.setItem(`${storageKeyPrefix}.gcp.bucket`, b.name);
      } catch {
        /* ignore */
      }
      onBucketChangeRef.current?.(b.name, b.location || null);
    },
    [storageKeyPrefix]
  );

  const displayBuckets = useMemo(() => {
    if (!platformMultiRegion || !platformRegionSlug) return buckets;
    const filtered = buckets.filter((b) => b.platform_slug === platformRegionSlug);
    return filtered.length ? filtered : buckets;
  }, [buckets, platformMultiRegion, platformRegionSlug]);

  useEffect(() => {
    if (!platformMultiRegion || !platformRegionSlug || !buckets.length) return;
    const match = buckets.find((b) => b.platform_slug === platformRegionSlug);
    if (match && selectedBucketRef.current !== match.name) {
      selectBucket(match);
    }
  }, [platformMultiRegion, platformRegionSlug, buckets, selectBucket]);

  const selectedMeta = displayBuckets.find((b) => b.name === selectedBucket);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await loadBuckets();
  }, [loadBuckets]);

  return {
    buckets: displayBuckets,
    mode,
    platformMultiRegion,
    platformRegions: platformRegionsFromBuckets(buckets),
    projectId,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectBucket,
    refresh,
    staticPlatformCatalog: mode === 'platform',
  };
}
