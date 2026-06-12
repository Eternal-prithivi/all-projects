import React, { useCallback, useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../../api';

const ACTION_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'plan', label: 'Plan' },
  { id: 'apply', label: 'Apply' },
  { id: 'destroy', label: 'Destroy' },
  { id: 'drift_check', label: 'Drift' },
  { id: 'remediate', label: 'Remediate' },
  { id: 'policy', label: 'Policies' },
];

const PERIOD_FILTERS = [
  { id: 7, label: '7 days' },
  { id: 30, label: '30 days' },
  { id: 90, label: '90 days' },
];

const ACTION_LABELS = {
  plan: 'Terraform plan',
  apply: 'Deploy apply',
  destroy: 'Stack destroy',
  drift_check: 'Drift check',
  remediate: 'Drift remediate',
  policy_create: 'Policy created',
  policy_update: 'Policy updated',
  policy_delete: 'Policy deleted',
  role_assign: 'Role assignment',
};

const ACTION_ICONS = {
  plan: '📋',
  apply: '🚀',
  destroy: '🗑️',
  drift_check: '🔍',
  remediate: '🔧',
  policy_create: '📜',
  policy_update: '✏️',
  policy_delete: '🗑️',
};

const formatRelativeTime = (timestamp) => {
  if (!timestamp) return '—';
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hr ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  return date.toLocaleString();
};

const describeEvent = (ev) => {
  const action = ev.action || 'unknown';
  const label = ACTION_LABELS[action] || action.replace(/_/g, ' ');
  const deployment = ev.deployment_id && ev.deployment_id !== 'governance'
    ? ev.deployment_id
    : null;
  const parts = [label];
  if (deployment) parts.push(`deployment ${deployment.slice(0, 8)}…`);
  if (ev.error) parts.push(ev.error);
  else if (ev.details?.rule_name) parts.push(`rule: ${ev.details.rule_name}`);
  else if (ev.details?.builtin_name) parts.push(`policy: ${ev.details.builtin_name}`);
  return parts.join(' · ');
};

export default function ProvisionActivityPanel() {
  const [actionFilter, setActionFilter] = useState('all');
  const [periodDays, setPeriodDays] = useState(90);
  const [page, setPage] = useState(0);
  const [data, setData] = useState({
    events: [],
    total: 0,
    has_more: false,
    limit: 10,
    period_days: 90,
    retention_days: 90,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  const limit = 10;

  const fetchPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/provision/audit-log', {
        params: {
          limit,
          skip: page * limit,
          action: actionFilter,
          period_days: periodDays,
        },
      });
      setData({
        events: res.data.events || [],
        total: res.data.total ?? 0,
        has_more: !!res.data.has_more,
        limit: res.data.limit ?? limit,
        period_days: res.data.period_days ?? periodDays,
        retention_days: res.data.retention_days ?? 90,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load activity'));
    } finally {
      setLoading(false);
    }
  }, [actionFilter, page, periodDays]);

  useEffect(() => {
    fetchPage();
  }, [fetchPage]);

  useEffect(() => {
    setPage(0);
  }, [actionFilter, periodDays]);

  const totalPages = Math.max(1, Math.ceil(data.total / limit));
  const rangeStart = data.total === 0 ? 0 : page * limit + 1;
  const rangeEnd = Math.min((page + 1) * limit, data.total);

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const res = await api.get('/provision/audit-log/export', {
        params: { period_days: periodDays, action: actionFilter },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `zenith_provision_audit_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError('CSV export failed');
    } finally {
      setExporting(false);
    }
  };

  if (error && !loading && data.events.length === 0) {
    return <div className="provision-empty-state"><p>{error}</p></div>;
  }

  return (
    <div className="provision-activity-panel">
      <div className="provision-activity-header">
        <div>
          <h3>Infrastructure activity</h3>
          <p className="provision-activity-subtitle">
            Audit trail for plan, apply, destroy, drift, and policy changes.
            {data.total > 0 && (
              <> Showing {rangeStart}–{rangeEnd} of {data.total} (last {data.period_days} days)</>
            )}
          </p>
          <p className="provision-activity-retention-hint">
            Events older than {data.retention_days} days are removed automatically. Export CSV for long-term records.
          </p>
        </div>
        <div className="provision-activity-header-actions">
          <button
            type="button"
            className="btn-provision secondary"
            onClick={handleExportCsv}
            disabled={exporting || loading}
          >
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
          <button
            type="button"
            className="btn-provision secondary"
            onClick={() => fetchPage()}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="provision-activity-filters" role="tablist" aria-label="Time window">
        {PERIOD_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={periodDays === f.id}
            className={`provision-filter-chip ${periodDays === f.id ? 'active' : ''}`}
            onClick={() => setPeriodDays(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="provision-activity-filters" role="tablist" aria-label="Filter by action">
        {ACTION_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={actionFilter === f.id}
            className={`provision-filter-chip ${actionFilter === f.id ? 'active' : ''}`}
            onClick={() => setActionFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="provision-activity-body">
        {loading && data.events.length === 0 ? (
          <div className="provision-loading">
            <div className="provision-spinner" />
            <span>Loading activity…</span>
          </div>
        ) : data.events.length === 0 ? (
          <div className="provision-empty-state">
            <p>No infrastructure actions match this filter.</p>
            <p className="provision-empty-hint">
              Plan, apply, drift checks, destroys, and policy edits appear here.
            </p>
          </div>
        ) : (
          <div className="provision-activity-timeline">
            {data.events.map((ev, i) => {
              const action = ev.action || 'unknown';
              const icon = ACTION_ICONS[action] || '📋';
              return (
                <div key={`${ev.timestamp}-${action}-${i}`} className="provision-activity-entry">
                  <span className="provision-activity-dot" aria-hidden="true" />
                  <div className="provision-activity-content">
                    <div className="provision-activity-title-row">
                      <h4>
                        {icon} {ACTION_LABELS[action] || action}
                      </h4>
                      <span className={`provision-activity-status-pill status-${ev.status || 'unknown'}`}>
                        {ev.status || '—'}
                      </span>
                    </div>
                    <p>{describeEvent(ev)}</p>
                    <div className="provision-activity-meta">
                      <span>{formatRelativeTime(ev.timestamp)}</span>
                      <span>{ev.actor}</span>
                      {ev.deployment_id && ev.deployment_id !== 'governance' && (
                        <span className="provision-activity-tag">stack</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {data.total > limit && (
        <div className="provision-activity-pagination">
          <button
            type="button"
            className="btn-provision secondary"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <span className="provision-page-indicator">
            Page {page + 1} of {totalPages}
          </span>
          <button
            type="button"
            className="btn-provision secondary"
            disabled={!data.has_more || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
