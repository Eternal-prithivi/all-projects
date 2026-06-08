import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FaCheckCircle, FaExclamationTriangle, FaHeartbeat, FaTools } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/status-page.css';

import { apiUrl } from '../config/apiBase.js';

const SERVICE_LABELS = {
  api: 'API',
  database: 'Database',
  billing_data: 'Billing data',
};

const SERVICE_STATE_LABELS = {
  operational: 'Operational',
  degraded: 'Degraded',
  maintenance: 'Maintenance',
  demo_mock: 'Demo mode (mock data)',
  live_apis: 'Live APIs',
};

const CLOUD_FEATURE_LABELS = {
  storage: 'Storage',
  billing: 'Billing',
  secure_vault: 'Secure vault',
  provision: 'Provision',
  vm: 'Virtual machines',
};

const PROVIDER_LABELS = {
  aws: 'AWS',
  gcp: 'GCP',
  azure: 'Azure',
};

const CLOUD_STATE_LABELS = {
  configured: 'Configured',
  not_configured: 'Not configured',
  not_supported: 'Not supported',
};

function serviceStateClass(state) {
  if (state === 'operational' || state === 'live_apis') return 'ok';
  if (state === 'demo_mock') return 'info';
  if (state === 'maintenance' || state === 'degraded') return 'warn';
  return 'neutral';
}

function cloudStateClass(state) {
  if (state === 'configured') return 'ok';
  if (state === 'not_supported') return 'neutral';
  if (state === 'not_configured') return 'warn';
  return 'neutral';
}

function overallBanner(loading, error, overall) {
  if (loading) {
    return { text: 'Checking platform health…', icon: <FaHeartbeat />, className: 'loading' };
  }
  if (error) {
    return { text: 'Unable to reach API', icon: <FaExclamationTriangle />, className: 'error' };
  }
  if (overall === 'operational') {
    return { text: 'All systems operational', icon: <FaCheckCircle />, className: 'ok' };
  }
  if (overall === 'maintenance') {
    return { text: 'Scheduled maintenance', icon: <FaTools />, className: 'warn' };
  }
  return { text: 'Partial degradation', icon: <FaExclamationTriangle />, className: 'warn' };
}

function formatServiceName(key) {
  return SERVICE_LABELS[key] || key.replace(/_/g, ' ');
}

function formatServiceState(state) {
  return SERVICE_STATE_LABELS[state] || state.replace(/_/g, ' ');
}

function formatCloudFeature(key) {
  return CLOUD_FEATURE_LABELS[key] || key.replace(/_/g, ' ');
}

function formatProvider(key) {
  return PROVIDER_LABELS[key] || key.toUpperCase();
}

function formatCloudState(state) {
  return CLOUD_STATE_LABELS[state] || state.replace(/_/g, ' ');
}

export default function StatusPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async (isInitial = false) => {
      try {
        const res = await fetch(apiUrl('/platform/status'));
        if (!res.ok) throw new Error('Status unavailable');
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message || 'Could not load status');
          if (isInitial) setData(null);
        }
      } finally {
        if (!cancelled && isInitial) setLoading(false);
      }
    };

    load(true);
    const id = setInterval(() => load(false), 60000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const banner = overallBanner(loading, error, data?.overall);
  const cloud = data?.cloud_connectivity;
  const providers = cloud?.providers ? Object.entries(cloud.providers) : [];

  return (
    <MarketingPageLayout showFooter>
      <div className="status-page">
        <header className="status-page__header">
          <span className="status-page__icon" aria-hidden="true">
            <FaHeartbeat />
          </span>
          <h1>System status</h1>
          <p>Live health for Zenith platform services — refreshes every 60 seconds</p>
        </header>

        <div className={`status-banner status-banner--${banner.className}`} role="status" aria-live="polite">
          <span className="status-banner__icon">{banner.icon}</span>
          <div>
            <strong>{banner.text}</strong>
            {data?.platform_name && !loading && !error && (
              <p className="status-banner__meta">{data.platform_name}</p>
            )}
            {data?.checked_at && !loading && (
              <p className="status-banner__meta">
                Last checked {new Date(data.checked_at).toLocaleString()}
                {data.demo_mode && ' · Demo mode enabled'}
              </p>
            )}
            {error && !loading && (
              <p className="status-banner__meta">
                Ensure the API is running (e.g. <code>localhost:8000</code>) and try again.
              </p>
            )}
          </div>
        </div>

        {!loading && data?.services && (
          <section className="status-section" aria-labelledby="status-platform-heading">
            <h2 id="status-platform-heading">Platform services</h2>
            <ul className="status-services">
              {Object.entries(data.services).map(([name, state]) => (
                <li key={name}>
                  <span className="status-services__name">{formatServiceName(name)}</span>
                  <span className={`status-pill status-pill--${serviceStateClass(state)}`}>
                    {formatServiceState(state)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {!loading && providers.length > 0 && (
          <section className="status-section" aria-labelledby="status-cloud-heading">
            <h2 id="status-cloud-heading">Cloud connectivity</h2>
            <p className="status-section__hint">
              Platform <code>.env</code> credential probes — no live cloud API calls from this page.
              {cloud?.summary?.any_storage_ready
                ? ` ${cloud.summary.storage_ready_count} of ${cloud.summary.total_providers} providers have storage configured.`
                : ' No provider storage is fully configured yet.'}
            </p>
            <div className="status-cloud-grid">
              {providers.map(([providerKey, features]) => (
                <article key={providerKey} className="status-cloud-card">
                  <h3>{formatProvider(providerKey)}</h3>
                  <ul>
                    {Object.entries(features).map(([featureKey, state]) => (
                      <li key={featureKey}>
                        <span>{formatCloudFeature(featureKey)}</span>
                        <span className={`status-pill status-pill--${cloudStateClass(state)}`}>
                          {formatCloudState(state)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </section>
        )}

        {loading && (
          <div className="status-loading" aria-busy="true">
            <div className="status-loading__bar" />
            <p>Fetching status from API…</p>
          </div>
        )}

        <p className="status-page__footer-note">
          Issues? <Link to="/contact">Contact support</Link> · <Link to="/trust">Trust center</Link>
        </p>
      </div>
    </MarketingPageLayout>
  );
}
