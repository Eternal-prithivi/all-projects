import React, { useEffect, useState } from 'react';
import api from '../../api';

const formatTime = (ts) => {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return String(ts);
  }
};

export default function ProvisionActivityPanel() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get('/provision/audit-log', { params: { limit: 50 } });
        if (!cancelled) setEvents(res.data.events || []);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Failed to load activity');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="provision-loading">
        <div className="provision-spinner" />
        <span>Loading provision activity…</span>
      </div>
    );
  }

  if (error) {
    return <div className="provision-empty-state"><p>{error}</p></div>;
  }

  if (events.length === 0) {
    return (
      <div className="provision-empty-state">
        <p>No infrastructure actions recorded yet.</p>
        <p className="provision-empty-hint">Plan, apply, drift checks, and destroys appear here.</p>
      </div>
    );
  }

  return (
    <div className="provision-activity-panel">
      <div className="section-header">
        <h3>Provision activity</h3>
        <p>Audit trail for infrastructure plan, apply, destroy, and drift on your account.</p>
      </div>
      <div className="provision-activity-list">
        {events.map((ev, i) => (
          <div key={ev._id || i} className="provision-activity-row">
            <div className="provision-activity-main">
              <span className={`provision-activity-status status-${ev.status || 'unknown'}`}>
                {ev.status || '—'}
              </span>
              <strong>{ev.action}</strong>
              <span className="provision-activity-meta">
                {ev.actor} · {ev.deployment_id || '—'}
              </span>
            </div>
            <time className="provision-activity-time">{formatTime(ev.timestamp)}</time>
          </div>
        ))}
      </div>
    </div>
  );
}
