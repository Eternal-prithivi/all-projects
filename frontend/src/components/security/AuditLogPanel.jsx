import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../api';

const CATEGORIES = [
  { id: 'all', label: 'All events' },
  { id: 'auth', label: 'Sign-ins' },
  { id: 'security', label: 'Security' },
  { id: 'account', label: 'Account' },
];

const formatRelativeTime = (timestamp) => {
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

const getAuditIcon = (category) => {
  const icons = { auth: '🔐', security: '🛡️', account: '👤', other: '📋' };
  return icons[category] || icons.other;
};

const AuditLogPanel = ({ onClose }) => {
  const [category, setCategory] = useState('all');
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0, has_more: false, period_days: 30 });
  const [loading, setLoading] = useState(true);

  const limit = 15;

  const fetchPage = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/profile/activity', {
        params: {
          limit,
          skip: page * limit,
          period_days: 30,
          category,
        },
      });
      setData(response.data);
    } catch (error) {
      console.error('Failed to load audit log:', error);
    } finally {
      setLoading(false);
    }
  }, [category, page]);

  useEffect(() => {
    fetchPage();
  }, [fetchPage]);

  useEffect(() => {
    setPage(0);
  }, [category]);

  const totalPages = Math.max(1, Math.ceil(data.total / limit));

  return (
    <div className="audit-panel" role="dialog" aria-label="Activity history">
      <div className="audit-panel-header">
        <div>
          <h3>Activity history</h3>
          <p className="audit-panel-subtitle">
            Last {data.period_days} days · {data.total} event{data.total !== 1 ? 's' : ''}
            {category !== 'all' ? ` · filtered` : ''}
          </p>
        </div>
        <button type="button" className="audit-panel-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      <div className="audit-filters" role="tablist" aria-label="Filter by category">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            type="button"
            role="tab"
            aria-selected={category === cat.id}
            className={`audit-filter-chip ${category === cat.id ? 'active' : ''}`}
            onClick={() => setCategory(cat.id)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="audit-panel-body">
        {loading ? (
          <p className="audit-empty">Loading…</p>
        ) : data.items.length > 0 ? (
          <div className="audit-timeline audit-timeline--compact">
            {data.items.map((activity, index) => (
              <div key={`${activity.timestamp}-${index}`} className="audit-entry">
                <span className="audit-dot" aria-hidden="true" />
                <div>
                  <h4>
                    {getAuditIcon(activity.category)} {activity.action}
                  </h4>
                  <p>{activity.description}</p>
                  <div className="audit-meta">
                    <span>{formatRelativeTime(activity.timestamp)}</span>
                    {activity.ip && activity.ip !== '—' && activity.ip !== '0.0.0.0' && (
                      <span>IP {activity.ip}</span>
                    )}
                    <span className="audit-category-tag">{activity.category}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="audit-empty">No events match this filter in the last 30 days.</p>
        )}
      </div>

      {data.total > limit && (
        <div className="audit-pagination">
          <button
            type="button"
            className="btn-secondary-outline"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <span className="audit-page-indicator">
            Page {page + 1} of {totalPages}
          </span>
          <button
            type="button"
            className="btn-secondary-outline"
            disabled={!data.has_more || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default AuditLogPanel;
