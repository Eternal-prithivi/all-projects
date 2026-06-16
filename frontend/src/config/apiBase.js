/**
 * Normalized API URLs for fetch() and axios.
 *
 * Vercel production must set:
 *   VITE_API_URL=https://api.rajverse.me
 * (no trailing /api)
 */

const PRODUCTION_API_ROOT = 'https://api.rajverse.me';
const LEGACY_PRODUCTION_API_ROOT = 'https://zenith-backend-707i.onrender.com';
const DEV_API_ROOT = 'http://localhost:8000';

function isLocalhostUrl(url) {
  return /localhost|127\.0\.0\.1/i.test(url);
}

/** Backend origin only (no /api suffix). */
export function getApiRoot() {
  const isProd = import.meta.env.MODE === 'production';
  const fromEnv = import.meta.env.VITE_API_URL
    ? String(import.meta.env.VITE_API_URL).replace(/\/api\/?$/i, '').replace(/\/$/, '')
    : '';

  if (isProd) {
    // Never call localhost from rajverse.me — common mis-set Vercel env
    if (fromEnv && !isLocalhostUrl(fromEnv)) {
      // Old Render hostname without the trailing "i" returns 404
      if (/zenith-backend-707\.onrender\.com/i.test(fromEnv) && !/707i/i.test(fromEnv)) {
        return LEGACY_PRODUCTION_API_ROOT;
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
