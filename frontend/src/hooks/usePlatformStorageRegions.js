import { useEffect, useState } from 'react';
import { getAwsBuckets } from '../api';
import { minLoadingDelay } from '../utils/minLoadingDelay';
import { platformRegionsFromBuckets } from './useAwsBuckets';

/**
 * Load platform multi-region metadata once (independent of AWS panel visibility).
 */
export function usePlatformStorageRegions({ enabled = true, reloadToken = 0 } = {}) {
  const [platformMultiRegion, setPlatformMultiRegion] = useState(false);
  const [platformRegions, setPlatformRegions] = useState([]);
  const [defaultPlatformSlug, setDefaultPlatformSlug] = useState('');
  const [mode, setMode] = useState('platform');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      const startedAt = Date.now();
      setLoading(true);
      try {
        const data = await getAwsBuckets('storage', {});
        if (cancelled) return;
        const list = data.buckets || [];
        const regions = platformRegionsFromBuckets(list);
        setPlatformMultiRegion(Boolean(data.platform_multi_region));
        setPlatformRegions(regions);
        setDefaultPlatformSlug(data.default_platform_slug || regions[0]?.slug || '');
        setMode(data.mode || 'platform');
      } catch {
        if (!cancelled) {
          setPlatformMultiRegion(false);
          setPlatformRegions([]);
        }
      } finally {
        if (!cancelled) {
          await minLoadingDelay(startedAt);
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled, reloadToken]);

  return {
    platformMultiRegion,
    platformRegions,
    defaultPlatformSlug,
    mode,
    loading,
  };
}
