import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '../api';
import { useAuth } from '../context/AuthContext.jsx';

const EMPTY = {
  plan_id: 'free',
  plan_name: 'Free',
  limits: { vm_limit: 2, storage_gb: 10, vms_used: 0, storage_bytes_used: 0 },
  features: {},
  nav: [],
};

export function usePlanEntitlements() {
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    if (!token) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get('/payments/entitlements');
      setData(res.data);
    } catch (e) {
      setError(e);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    reload();
  }, [reload]);

  const entitlements = data || EMPTY;

  const navById = useMemo(() => {
    const map = {};
    for (const item of entitlements.nav || []) {
      map[item.id] = item;
    }
    return map;
  }, [entitlements.nav]);

  const isFeatureEnabled = useCallback(
    (featureKey) => Boolean(entitlements.features?.[featureKey]),
    [entitlements.features]
  );

  const isNavLocked = useCallback(
    (navId) => Boolean(navById[navId]?.locked),
    [navById]
  );

  const getNavMeta = useCallback((navId) => navById[navId] || null, [navById]);

  return {
    loading,
    error,
    entitlements,
    planId: entitlements.plan_id,
    planName: entitlements.plan_name,
    limits: entitlements.limits,
    features: entitlements.features,
    reload,
    isFeatureEnabled,
    isNavLocked,
    getNavMeta,
  };
}
