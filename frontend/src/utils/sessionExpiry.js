/**
 * Global session expiry handler — used by apiClient 401 interceptor and AuthContext.
 */
import { notifyWarning } from './notifications.js';

let handling = false;

const AUTH_PATH_PREFIXES = [
  '/auth/token',
  '/auth/register',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/verify-email',
  '/auth/refresh',
  '/auth/logout',
  '/auth/sso/',
];

function isAuthRequest(url) {
  if (!url) return false;
  const path = String(url);
  return AUTH_PATH_PREFIXES.some((p) => path.includes(p));
}

/**
 * Clear session and notify user (once per page lifecycle until login).
 */
export function triggerSessionExpired(options = {}) {
  const { redirect = true, message } = options;
  if (handling) return;
  handling = true;

  sessionStorage.removeItem('cachedUser');

  const text =
    message ||
    'Your session has ended. Please sign in again to continue.';

  notifyWarning(text, {
    title: 'Session expired',
    autoClose: 12000,
  });

  if (redirect && typeof window !== 'undefined') {
    const path = window.location.pathname || '';
    if (!path.startsWith('/login') && !path.startsWith('/register')) {
      const from = encodeURIComponent(path + window.location.search);
      window.setTimeout(() => {
        window.location.href = `/login?session=expired&from=${from}`;
      }, 300);
    }
  }
}

export function resetSessionExpiredGuard() {
  handling = false;
}

export function shouldHandle401(config) {
  if (!config) return true;
  return !isAuthRequest(config.url);
}
