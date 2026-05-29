import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FaCheckCircle, FaExclamationTriangle, FaTools } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/status-page.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function statusLabel(overall) {
  if (overall === 'operational') return { text: 'All systems operational', icon: <FaCheckCircle />, className: 'ok' };
  if (overall === 'maintenance') return { text: 'Scheduled maintenance', icon: <FaTools />, className: 'warn' };
  return { text: 'Partial degradation', icon: <FaExclamationTriangle />, className: 'warn' };
}

export default function StatusPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/platform/status`);
        if (!res.ok) throw new Error('Status unavailable');
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setError(e.message || 'Could not load status');
      }
    };
    load();
    const id = setInterval(load, 60000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const banner = statusLabel(data?.overall || (error ? 'degraded' : 'operational'));

  return (
    <MarketingPageLayout showFooter>
      <div className="status-page">
        <header className="status-page__header reveal-group">
          <div className="reveal-item">
            <h1>System status</h1>
            <p>Live health for Zenith platform services</p>
          </div>
        </header>

        <div className={`status-banner status-banner--${banner.className} reveal-item`}>
          <span className="status-banner__icon">{banner.icon}</span>
          <div>
            <strong>{error ? 'Unable to reach API' : banner.text}</strong>
            {data?.checked_at && (
              <p className="status-banner__meta">Last checked {new Date(data.checked_at).toLocaleString()}</p>
            )}
          </div>
        </div>

        {data?.services && (
          <ul className="status-services reveal-item">
            {Object.entries(data.services).map(([name, state]) => (
              <li key={name}>
                <span className="status-services__name">{name}</span>
                <span className={`status-services__state status-services__state--${state}`}>{state}</span>
              </li>
            ))}
          </ul>
        )}

        <p className="status-page__footer-note reveal-item">
          Issues? <Link to="/contact">Contact support</Link> · <Link to="/trust">Trust center</Link>
        </p>
      </div>
    </MarketingPageLayout>
  );
}
