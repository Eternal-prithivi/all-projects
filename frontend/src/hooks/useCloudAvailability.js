import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api';

const EMPTY_FEATURE = {
  providers: [],
  default: null,
  multi_provider: false,
};

/**
 * Canonical display labels for CSP selectors (AWS | GCP | Azure).
 */
export const CSP_LABELS = {
  AWS: 'AWS',
  GCP: 'GCP',
  Azure: 'Azure',
};

/** Lowercase keys for Cost API routes */
export const CSP_TO_COST_KEY = {
  AWS: 'aws',
  GCP: 'gcp',
  Azure: 'azure',
};

export const COST_KEY_TO_CSP = {
  aws: 'AWS',
  gcp: 'GCP',
  azure: 'Azure',
};

/**
 * Build select options for CloudProviderToolbar.
 * @param {string[]} providers - e.g. ['AWS', 'GCP']
 * @param {{ includeAll?: boolean, allLabel?: string }} opts
 */
export function buildCloudProviderOptions(providers = [], opts = {}) {
  const { includeAll = true, allLabel = 'All connected' } = opts;
  const list = Array.isArray(providers) ? providers : [];
  const options = [];
  if (includeAll && list.length > 1) {
    options.push({ value: 'ALL', label: allLabel });
  }
  for (const p of list) {
    options.push({ value: p, label: CSP_LABELS[p] || p });
  }
  return options;
}

/**
 * Pick a valid provider when the current selection is no longer allowed.
 */
export function coerceCloudProvider(current, providers, { allowAll = true } = {}) {
  const list = providers || [];
  if (!list.length) return null;
  if (list.length === 1) return list[0];
  if (allowAll && current === 'ALL') return 'ALL';
  if (list.includes(current)) return current;
  return list[0];
}

export function useCloudAvailability() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get('/cloud/availability');
      setData(res.data);
    } catch (e) {
      setError(e);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const getFeature = useCallback(
    (feature) => data?.features?.[feature] || EMPTY_FEATURE,
    [data]
  );

  return {
    loading,
    error,
    data,
    reload,
    credentialMode: data?.credential_mode || 'platform',
    byocConnected: data?.byoc_connected || [],
    getFeature,
  };
}
