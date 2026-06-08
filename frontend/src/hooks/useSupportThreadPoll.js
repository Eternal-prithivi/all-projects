import { useEffect, useRef } from 'react';

const DEFAULT_INTERVAL_MS = 10000;

/**
 * Poll a callback on an interval; pauses when the document tab is hidden.
 */
export function useSupportThreadPoll(callback, { enabled = true, intervalMs = DEFAULT_INTERVAL_MS } = {}) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return undefined;

    let id = null;

    const tick = () => {
      if (document.hidden) return;
      callbackRef.current?.();
    };

    const start = () => {
      if (id) clearInterval(id);
      id = setInterval(tick, intervalMs);
    };

    const onVisibility = () => {
      if (!document.hidden) tick();
    };

    start();
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      if (id) clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [enabled, intervalMs]);
}
