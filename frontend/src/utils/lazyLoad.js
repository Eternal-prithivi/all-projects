import { lazy } from 'react';

const CHUNK_RELOAD_KEY = 'zenith-chunk-reload';

function isChunkLoadError(err) {
  const msg = err?.message || '';
  return (
    err?.name === 'ChunkLoadError' ||
    msg.includes('Failed to fetch dynamically imported module') ||
    msg.includes('is not a valid JavaScript MIME type') ||
    msg.includes('Loading chunk') ||
    msg.includes('Loading CSS chunk')
  );
}

/**
 * Dynamic import with one automatic full reload when a lazy chunk 404s after deploy
 * (Vercel SPA fallback used to return index.html for missing /assets/*.js).
 */
export async function importWithRetry(factory) {
  try {
    const mod = await factory();
    sessionStorage.removeItem(CHUNK_RELOAD_KEY);
    return mod;
  } catch (err) {
    if (isChunkLoadError(err) && !sessionStorage.getItem(CHUNK_RELOAD_KEY)) {
      sessionStorage.setItem(CHUNK_RELOAD_KEY, '1');
      window.location.reload();
      return new Promise(() => {});
    }
    sessionStorage.removeItem(CHUNK_RELOAD_KEY);
    throw err;
  }
}

export function lazyWithRetry(factory) {
  return lazy(() => importWithRetry(factory));
}
