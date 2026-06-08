import { useEffect } from 'react';
import { useAuth } from '../../context/AuthContext.jsx';
import { useNotificationCenter } from '../../context/NotificationContext.jsx';
import { dispatchSupportWsEvent } from '../../utils/supportEventBus.js';

function wsUrlForToken(token) {
  return import.meta.env.DEV
    ? `ws://localhost:8000/ws/status?token=${token}`
    : `wss://zenith-backend-707i.onrender.com/ws/status?token=${token}`;
}

/**
 * Single WebSocket per layout session — dispatches support events to the event bus
 * and surfaces customer-facing notifications for agent replies.
 */
export default function SupportWsBridge({ notifyOnAgentReply = false }) {
  const { token } = useAuth();
  const { addNotification } = useNotificationCenter();

  useEffect(() => {
    if (!token) return undefined;

    const ws = new WebSocket(wsUrlForToken(token));

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data?.event) return;

        if (data.event === 'support_reply' || data.event === 'support_customer_reply') {
          dispatchSupportWsEvent(data);
        }

        if (
          notifyOnAgentReply &&
          data.event === 'support_reply' &&
          data.reference_code
        ) {
          addNotification({
            title: 'Support replied',
            message: `New reply on ${data.reference_code}`,
            type: 'info',
            link: `/dashboard/support?ref=${encodeURIComponent(data.reference_code)}`,
            persist: true,
          });
        }
      } catch {
        /* non-JSON payloads (e.g. job_complete) */
      }
    };

    return () => ws.close();
  }, [token, notifyOnAgentReply, addNotification]);

  return null;
}
