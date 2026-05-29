/**
 * Optional Sentry — enabled only when VITE_SENTRY_DSN is set at build time.
 */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  import('@sentry/react').then((Sentry) => {
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE,
      integrations: [Sentry.browserTracingIntegration()],
      tracesSampleRate: 0.1,
    });
  }).catch((err) => {
    console.warn('Sentry init skipped:', err);
  });
}
