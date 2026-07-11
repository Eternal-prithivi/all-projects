/**
 * Normalized API URLs for fetch() and axios.
 *
 * rajverse.me (production): same-origin /api via Vercel rewrite → Render backend.
 * Avoids ad blockers that block zenith-backend-707i.onrender.com (ERR_BLOCKED_BY_CLIENT).
 *
 * Custom API subdomain (optional): VITE_API_URL=https://api.rajverse.me
 */

/** Direct Render host — fallback when not on rajverse.me and no VITE_API_URL. */
const PRODUCTION_API_ROOT = 'https://zenith-backend-707i.onrender.com';
const DEV_API_ROOT = 'http://localhost:8000';

function isLocalhostUrl(url) {
  return /localhost|127\.0\.0\.1/i.test(url);
}

/** api.rajverse.me must resolve before use — see docs/setup/API_SUBDOMAIN.md */
function isUnconfiguredCustomApiHost(url) {
  return /^https:\/\/api\.rajverse\.me\/?$/i.test(String(url || '').replace(/\/$/, ''));
}

/** True when the SPA runs on rajverse.me and should use Vercel /api proxy (same origin). */
export function usesSameOriginApiProxy() {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname;
  return host === 'rajverse.me' || host.endsWith('.rajverse.me');
}

/** Backend origin only (no /api suffix). */
export function getApiRoot() {
  if (usesSameOriginApiProxy()) {
    return window.location.origin;
  }

  const isProd = import.meta.env.MODE === 'production';
  const fromEnv = import.meta.env.VITE_API_URL
    ? String(import.meta.env.VITE_API_URL).replace(/\/api\/?$/i, '').replace(/\/$/, '')
    : '';

  if (isProd) {
    if (fromEnv && !isLocalhostUrl(fromEnv) && !isUnconfiguredCustomApiHost(fromEnv)) {
      if (/zenith-backend-707\.onrender\.com/i.test(fromEnv) && !/707i/i.test(fromEnv)) {
        return PRODUCTION_API_ROOT;
      }
      return fromEnv;
    }
    return PRODUCTION_API_ROOT;
  }

  return fromEnv || DEV_API_ROOT;
}

/** Axios baseURL and fetch prefix for routes under /api/... */
export function getApiBaseUrl() {
  return `${getApiRoot()}/api`;
}

/** Build a full URL for routes under /api (e.g. /platform/status → .../api/platform/status). */
export function apiUrl(apiPath) {
  const path = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;
  const relative = path.startsWith('/api/') ? path.slice(4) : path;
  return `${getApiBaseUrl()}${relative.startsWith('/') ? relative : `/${relative}`}`;
}

/** WebSocket origin (ws/wss) aligned with getApiRoot(). */
export function getWsRoot() {
  const root = getApiRoot().replace(/\/$/, '');
  return root.replace(/^http/i, 'ws');
}
