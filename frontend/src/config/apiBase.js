/**
 * Normalized API URLs for fetch() and axios.
 *
 * VITE_API_URL should be the backend ROOT without /api, e.g.
 *   https://zenith-backend-707i.onrender.com
 * If it ends with /api, we strip it so callers never produce /api/api/...
 */

const PRODUCTION_API_ROOT = 'https://zenith-backend-707i.onrender.com';
const DEV_API_ROOT = 'http://localhost:8000';

/** Backend origin only (no /api suffix). */
export function getApiRoot() {
  const raw =
    import.meta.env.VITE_API_URL ||
    (import.meta.env.MODE === 'production' ? PRODUCTION_API_ROOT : DEV_API_ROOT);
  return String(raw).replace(/\/api\/?$/i, '').replace(/\/$/, '');
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
