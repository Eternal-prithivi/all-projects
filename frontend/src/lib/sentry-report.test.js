import { describe, expect, it, vi, beforeEach } from 'vitest';
import { reportError } from './sentry-report.js';

describe('reportError', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it('no-ops when VITE_SENTRY_DSN is unset', async () => {
    vi.stubEnv('VITE_SENTRY_DSN', '');
    const capture = vi.fn();
    vi.doMock('@sentry/react', () => ({ captureException: capture }));

    reportError(new Error('test'));
    await new Promise((r) => setTimeout(r, 0));
    expect(capture).not.toHaveBeenCalled();
  });
});
