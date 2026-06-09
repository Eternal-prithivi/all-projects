import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getAzureContainers } from '../api';
import { minLoadingDelay } from '../utils/minLoadingDelay';
import { platformRegionsFromBuckets } from './useAwsBuckets';

/**
 * Load Azure Blob containers for Storage destination picker.
 */
export function useAzureContainers({
  storageKeyPrefix = 'zenith.storage',
  selectedContainer,
  onContainerChange,
  enabled = true,
  platformRegionSlug = null,
  reloadToken = 0,
  surface = 'storage',
}) {
  const [containers, setContainers] = useState([]);
  const [mode, setMode] = useState('platform');
  const [platformMultiRegion, setPlatformMultiRegion] = useState(false);
  const [accountName, setAccountName] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [discoveryError, setDiscoveryError] = useState(null);
  const didAutoSelect = useRef(false);
  const didInitialLoad = useRef(false);
  const selectedContainerRef = useRef(selectedContainer);
  const onContainerChangeRef = useRef(onContainerChange);
  selectedContainerRef.current = selectedContainer;
  onContainerChangeRef.current = onContainerChange;

  const loadContainers = useCallback(async () => {
    if (!enabled) {
      setContainers([]);
      setLoading(false);
      return;
    }
    const startedAt = Date.now();
    setLoading(true);
    try {
      const data = await getAzureContainers({ surface });
      const list = data.containers || [];
      setContainers(list);
      setMode(data.mode || 'platform');
      setPlatformMultiRegion(Boolean(data.platform_multi_region));
      setAccountName(data.account_name || null);
      setDiscoveryError(data.error || null);

      if (list.length && !selectedContainerRef.current && !didAutoSelect.current) {
        let stored = null;
        try {
          stored = sessionStorage.getItem(`${storageKeyPrefix}.azure.container`);
        } catch {
          /* ignore */
        }
        const pick =
          list.find((c) => c.name === stored) ||
          list.find((c) => c.is_default) ||
          list[0];
        didAutoSelect.current = true;
        onContainerChangeRef.current?.(pick.name);
      }
    } catch (e) {
      const msg = e?.detail || e?.message || 'Could not load Azure containers.';
      setDiscoveryError(typeof msg === 'string' ? msg : 'Could not load Azure containers.');
      setContainers([]);
    } finally {
      await minLoadingDelay(startedAt);
      setLoading(false);
      setRefreshing(false);
    }
  }, [enabled, storageKeyPrefix, reloadToken, surface]);

  useEffect(() => {
    if (!enabled) return;
    if (didInitialLoad.current) {
      setRefreshing(true);
    }
    didInitialLoad.current = true;
    loadContainers();
  }, [loadContainers, enabled]);

  const selectContainer = useCallback(
    (c) => {
      try {
        sessionStorage.setItem(`${storageKeyPrefix}.azure.container`, c.name);
      } catch {
        /* ignore */
      }
      onContainerChangeRef.current?.(c.name);
    },
    [storageKeyPrefix]
  );

  const displayContainers = useMemo(() => {
    if (!platformMultiRegion || !platformRegionSlug) return containers;
    const filtered = containers.filter((c) => c.platform_slug === platformRegionSlug);
    return filtered.length ? filtered : containers;
  }, [containers, platformMultiRegion, platformRegionSlug]);

  useEffect(() => {
    if (!platformMultiRegion || !platformRegionSlug || !containers.length) return;
    const match = containers.find((c) => c.platform_slug === platformRegionSlug);
    if (match && selectedContainerRef.current !== match.name) {
      selectContainer(match);
    }
  }, [platformMultiRegion, platformRegionSlug, containers, selectContainer]);

  const selectedMeta = displayContainers.find((c) => c.name === selectedContainer);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await loadContainers();
  }, [loadContainers]);

  return {
    containers: displayContainers,
    mode,
    platformMultiRegion,
    platformRegions: platformRegionsFromBuckets(containers),
    accountName,
    loading,
    refreshing,
    discoveryError,
    selectedMeta,
    selectContainer,
    refresh,
    staticPlatformCatalog: mode === 'platform',
  };
}
