/**
 * While the Zenith tab is open in production, ping Render /health periodically so the
 * free-tier backend does not spin down during active use. GitHub Actions handles idle periods.
 */
import { getApiRoot } from '../config/apiBase.js';

const INTERVAL_MS = 10 * 60 * 1000;

function shouldPing() {
  if (import.meta.env.MODE !== 'production') return false;
  const root = getApiRoot();
  return root && !/localhost|127\.0\.0\.1/i.test(root);
}

export function startRenderKeepAlive() {
  if (!shouldPing()) {
    return () => {};
  }

  const root = getApiRoot().replace(/\/$/, '');

  const ping = () => {
    fetch(`${root}/health`, {
      method: 'GET',
      cache: 'no-store',
      credentials: 'omit',
    }).catch(() => {});
  };

  ping();
  const timer = window.setInterval(ping, INTERVAL_MS);
  return () => window.clearInterval(timer);
}
