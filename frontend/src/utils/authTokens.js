/** Bearer token storage — used when api.rajverse.me cookies are unavailable (cross-origin Render API). */

import { getApiRoot } from '../config/apiBase.js';

const ACCESS_KEY = 'authToken';
const REFRESH_KEY = 'refreshToken';
const CACHED_USER_KEY = 'cachedUser';

function getCachedUserSnapshot() {
  try {
    const raw = sessionStorage.getItem(CACHED_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** True when API cookies may be first-party (rajverse.me → api.rajverse.me). */
function isFirstPartyCookieAuth() {
  if (typeof window === 'undefined') return false;
  try {
    const apiHost = new URL(getApiRoot()).hostname;
    const pageHost = window.location.hostname;
    return pageHost.endsWith('rajverse.me') && apiHost.endsWith('rajverse.me');
  } catch {
    return false;
  }
}

export function isAccessTokenExpired(token) {
  if (!token) return true;
  try {
    const segment = token.split('.')[1];
    if (!segment) return false;
    const payload = JSON.parse(atob(segment.replace(/-/g, '+').replace(/_/g, '/')));
    if (!payload.exp) return false;
    return payload.exp * 1000 < Date.now() - 30_000;
  } catch {
    return false;
  }
}

export function clearStaleSessionArtifacts() {
  clearAuthTokens();
  try {
    sessionStorage.removeItem(CACHED_USER_KEY);
  } catch {
    /* ignore */
  }
}

/** Skip /users/me on cold load when there is no token, cache, or cookie domain match. */
export function shouldProbeSessionOnLoad() {
  const access = getStoredAccessToken();
  const refresh = getStoredRefreshToken();

  if (refresh) return true;
  if (access && !isAccessTokenExpired(access)) return true;
  if (access && isAccessTokenExpired(access)) {
    clearAuthTokens();
    return false;
  }

  // Orphaned cached user (no tokens) — clear locally, do not hit /me.
  if (getCachedUserSnapshot()) {
    try {
      sessionStorage.removeItem(CACHED_USER_KEY);
    } catch {
      /* ignore */
    }
    return false;
  }

  return isFirstPartyCookieAuth();
}

/** Avoid /auth/refresh when anonymous — prevents paired 401 console noise. */
export function canAttemptSessionRefresh() {
  if (getStoredRefreshToken()) return true;
  return isFirstPartyCookieAuth();
}

export function storeAuthTokens(data) {
  if (!data || typeof data !== 'object') return;
  if (data.access_token) {
    sessionStorage.setItem(ACCESS_KEY, data.access_token);
  }
  if (data.refresh_token) {
    sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
  }
}

export function getStoredAccessToken() {
  try {
    return sessionStorage.getItem(ACCESS_KEY);
  } catch {
    return null;
  }
}

export function getStoredRefreshToken() {
  try {
    return sessionStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function clearAuthTokens() {
  try {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  } catch {
    /* ignore */
  }
}
