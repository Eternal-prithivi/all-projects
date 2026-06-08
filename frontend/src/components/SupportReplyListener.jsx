import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { useNotificationCenter } from '../context/NotificationContext.jsx';

/**
 * Listens on the shared status WebSocket for support_reply events
 * and surfaces them via the notification center.
 */
export default function SupportReplyListener() {
  const { token } = useAuth();
  const { addNotification } = useNotificationCenter();

  useEffect(() => {
    if (!token) return undefined;

    const wsUrl = import.meta.env.DEV
      ? `ws://localhost:8000/ws/status?token=${token}`
      : `wss://zenith-backend-707i.onrender.com/ws/status?token=${token}`;

    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'support_reply' && data.reference_code) {
          addNotification({
            title: 'Support replied',
            message: `New reply on ${data.reference_code}`,
            type: 'info',
            link: `/dashboard/support?ref=${encodeURIComponent(data.reference_code)}`,
            persist: true,
          });
        }
      } catch {
        /* plain-text WS payloads (e.g. job_complete) — ignore */
      }
    };

    return () => ws.close();
  }, [token, addNotification]);

  return null;
}
