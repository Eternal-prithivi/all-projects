import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { importWithRetry } from './lazyLoad.js';

describe('importWithRetry', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.stubGlobal('location', { reload: vi.fn() });
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it('returns module on success', async () => {
    const mod = await importWithRetry(() => Promise.resolve({ default: 1 }));
    expect(mod.default).toBe(1);
  });

  it('reloads once on chunk MIME error', async () => {
    const factory = vi.fn().mockRejectedValueOnce(
      new TypeError("'text/html' is not a valid JavaScript MIME type")
    );

    void importWithRetry(factory);
    await Promise.resolve();
    expect(window.location.reload).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem('zenith-chunk-reload')).toBe('1');
  });
});
