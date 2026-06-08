import { useEffect } from 'react';
import { matchesSupportTarget, subscribeSupportWsEvent } from '../utils/supportEventBus.js';

/**
 * Refetch thread when a matching support WS event arrives on the shared event bus.
 */
export function useSupportThreadWs(
  onRefresh,
  { referenceCode, ticketId, events = ['support_reply', 'support_customer_reply'], enabled = true } = {}
) {
  useEffect(() => {
    if (!enabled || !onRefresh) return undefined;
    if (!referenceCode && !ticketId) return undefined;

    return subscribeSupportWsEvent((payload) => {
      if (!events.includes(payload?.event)) return;
      if (!matchesSupportTarget(payload, { referenceCode, ticketId })) return;
      onRefresh();
    });
  }, [enabled, onRefresh, referenceCode, ticketId, events]);
}
