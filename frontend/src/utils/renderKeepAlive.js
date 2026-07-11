/**
 * While the Zenith tab is open in production, ping Render /health/ready periodically so the
 * free-tier backend stays warm (MongoDB + deps), not just the lightweight /health probe.
 * GitHub Actions handles idle periods when no tab is open.
 */
import { getApiRoot } from '../config/apiBase.js';

/** Match GitHub Actions `render-keep-alive.yml` (every 5 minutes). */
const INTERVAL_MS = 5 * 60 * 1000;
/** Single request timeout — cold Docker start on Render can take 60–90s. */
const PING_TIMEOUT_MS = 120_000;
/** Retries when waking before login (user is waiting). */
const WAKE_MAX_ATTEMPTS = 3;
const WAKE_RETRY_DELAY_MS = 20_000;

function shouldPing() {
  if (import.meta.env.MODE !== 'production') return false;
  const root = getApiRoot();
  return root && !/localhost|127\.0\.0\.1/i.test(root);
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function pingHealthOnce(root) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), PING_TIMEOUT_MS);

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

async function pingReadyOnce(root) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), PING_TIMEOUT_MS);

  try {
    const res = await fetch(`${root}/health/ready`, {
      method: 'GET',
      cache: 'no-store',
      credentials: 'omit',
      signal: controller.signal,
    });
    if (!res.ok) return false;
    const body = await res.json().catch(() => ({}));
    return body.mongo_connected === true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/**
 * Warm the backend (MongoDB + deps). Used on login and periodic keep-alive.
 * Retries a few times because Render free-tier cold starts can exceed one minute.
 */
export async function wakeRenderBackend() {
  if (!shouldPing()) {
    return true;
  }

  const root = getApiRoot().replace(/\/$/, '');

  for (let attempt = 1; attempt <= WAKE_MAX_ATTEMPTS; attempt += 1) {
    const ready = await pingReadyOnce(root);
    if (ready) return true;
    const alive = await pingHealthOnce(root);
    if (alive) return true;
    if (attempt < WAKE_MAX_ATTEMPTS) {
      await sleep(WAKE_RETRY_DELAY_MS);
    }
  }
  return false;
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
