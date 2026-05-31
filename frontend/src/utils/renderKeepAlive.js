/**
 * While the Zenith tab is open in production, ping Render /health periodically so the
 * free-tier backend does not spin down during active use. GitHub Actions handles idle periods.
 */
import { getApiRoot } from '../config/apiBase.js';

/** Match GitHub Actions `render-keep-alive.yml` (every 5 minutes). */
const INTERVAL_MS = 5 * 60 * 1000;
const WAKE_TIMEOUT_MS = 90_000;

function shouldPing() {
  if (import.meta.env.MODE !== 'production') return false;
  const root = getApiRoot();
  return root && !/localhost|127\.0\.0\.1/i.test(root);
}

/** GET /health once (used on login and keep-alive). Returns true if backend responded OK. */
export async function wakeRenderBackend() {
  if (!shouldPing()) {
    return true;
  }

  const root = getApiRoot().replace(/\/$/, '');
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), WAKE_TIMEOUT_MS);

  try {
    const res = await fetch(`${root}/health`, {
      method: 'GET',
      cache: 'no-store',
      credentials: 'omit',
      signal: controller.signal,
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function startRenderKeepAlive() {
  if (!shouldPing()) {
    return () => {};
  }

  const ping = () => {
    wakeRenderBackend().catch(() => {});
  };

  ping();
  const timer = window.setInterval(ping, INTERVAL_MS);
  return () => window.clearInterval(timer);
}
