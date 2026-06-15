import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiClient } from "../api";

const CACHE_KEY = "cache_cloud_availability";
/** 5 minutes — short enough to pick up BYOC changes without a hard refresh. */
const CACHE_TTL_MS = 5 * 60 * 1000;

const EMPTY_FEATURE = {
  providers: [],
  default: null,
  multi_provider: false,
};

const CloudAvailabilityContext = createContext(null);

function readCache() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { data, ts } = JSON.parse(raw);
    if (!data || Date.now() - ts > CACHE_TTL_MS) {
      sessionStorage.removeItem(CACHE_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

function writeCache(data) {
  try {
    if (data) sessionStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }));
  } catch {
    /* ignore quota */
  }
}

/** Call this after any BYOC connect / disconnect to force a fresh fetch. */
export function invalidateCloudAvailabilityCache() {
  try {
    sessionStorage.removeItem(CACHE_KEY);
  } catch {
    /* ignore */
  }
}

export function CloudAvailabilityProvider({ children }) {
  const [data, setData] = useState(() => readCache());
  const [loading, setLoading] = useState(() => !readCache());
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get("/cloud/availability");
      setData(res.data);
      writeCache(res.data);
    } catch (e) {
      setError(e);
      if (!readCache()) setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const cached = readCache();
    if (cached) {
      return;
    }
    reload();
  }, [reload]);

  const getFeature = useCallback(
    (feature) => data?.features?.[feature] || EMPTY_FEATURE,
    [data]
  );

  const getCredentialSource = useCallback(
    (csp, feature = "storage") => {
      const feat = data?.features?.[feature];
      return feat?.credential_sources?.[csp] || data?.credential_sources?.[csp] || null;
    },
    [data]
  );

  const getLockedProviders = useCallback(
    (feature) => getFeature(feature).locked_providers || [],
    [getFeature]
  );

  const value = useMemo(
    () => ({
      loading,
      error,
      data,
      reload,
      credentialMode: data?.credential_mode || "platform",
      byocConnected: data?.byoc_connected || [],
      byocCapabilities: data?.byoc_capabilities || null,
      credentialSources: data?.credential_sources || {},
      getFeature,
      getCredentialSource,
      getLockedProviders,
    }),
    [
      loading,
      error,
      data,
      reload,
      getFeature,
      getCredentialSource,
      getLockedProviders,
    ]
  );

  return (
    <CloudAvailabilityContext.Provider value={value}>
      {children}
    </CloudAvailabilityContext.Provider>
  );
}

export function useCloudAvailabilityContext() {
  const ctx = useContext(CloudAvailabilityContext);
  if (!ctx) {
    throw new Error(
      "useCloudAvailability must be used within CloudAvailabilityProvider"
    );
  }
  return ctx;
}
