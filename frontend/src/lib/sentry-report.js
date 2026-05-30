/**
 * Report errors to Sentry when VITE_SENTRY_DSN is set.
 * Dynamic import keeps dev working when Sentry is disabled.
 */

export function reportError(error, errorInfo = null) {
  if (!import.meta.env.VITE_SENTRY_DSN) return;

  import('@sentry/react')
    .then((Sentry) => {
      Sentry.captureException(error, {
        contexts: errorInfo?.componentStack
          ? { react: { componentStack: errorInfo.componentStack } }
          : undefined,
      });
    })
    .catch(() => {
      /* Sentry package missing or init failed */
    });
}
