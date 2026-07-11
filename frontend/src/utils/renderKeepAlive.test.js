import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../config/apiBase.js', () => ({
  getApiRoot: vi.fn(() => 'https://zenith-backend-707i.onrender.com'),
}));

import { getApiRoot } from '../config/apiBase.js';
import { startRenderKeepAlive, wakeRenderBackend } from './renderKeepAlive.js';

describe('renderKeepAlive', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true })));
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('does not ping in development', () => {
    const stop = startRenderKeepAlive();
    stop();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('pings /health in production', () => {
    vi.stubEnv('MODE', 'production');
    fetch.mockResolvedValue({ ok: true });
    const stop = startRenderKeepAlive();
    expect(fetch).toHaveBeenCalledWith(
      'https://zenith-backend-707i.onrender.com/health',
      expect.objectContaining({ method: 'GET' })
    );
    vi.advanceTimersByTime(5 * 60 * 1000);
    expect(fetch).toHaveBeenCalledTimes(2);
    stop();
    vi.unstubAllEnvs();
  });

  it('wakeRenderBackend returns true when ready responds with mongo_connected', async () => {
    vi.stubEnv('MODE', 'production');
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ mongo_connected: true }) });
    await expect(wakeRenderBackend()).resolves.toBe(true);
    vi.unstubAllEnvs();
  });

  it('wakeRenderBackend falls back to /health when ready is not mongo-ready', async () => {
    vi.stubEnv('MODE', 'production');
    fetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ mongo_connected: false }) })
      .mockResolvedValueOnce({ ok: true });
    await expect(wakeRenderBackend()).resolves.toBe(true);
    vi.unstubAllEnvs();
  });

  it('skips ping when API root is localhost', () => {
    vi.stubEnv('MODE', 'production');
    getApiRoot.mockReturnValueOnce('http://localhost:8000');
    const stop = startRenderKeepAlive();
    stop();
    expect(fetch).not.toHaveBeenCalled();
    vi.unstubAllEnvs();
  });
});
