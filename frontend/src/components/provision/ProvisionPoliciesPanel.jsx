import React, { useEffect, useState } from 'react';
import api from '../../api';

export default function ProvisionPoliciesPanel() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get('/provision/policy-rules');
        if (!cancelled) setRules(res.data.rules || []);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Failed to load policies');
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
        <span>Loading policy rules…</span>
      </div>
    );
  }

  if (error) {
    return <div className="provision-empty-state"><p>{error}</p></div>;
  }

  return (
    <div className="provision-policies-panel">
      <div className="section-header">
        <h3>Governance policies</h3>
        <p>Rules evaluated before any new stack is deployed. Connect AWS in Settings — no duplicate setup here.</p>
      </div>
      <div className="policy-results">
        {rules.map((rule) => (
          <div
            key={rule.name}
            className={`policy-item ${rule.severity === 'block' ? 'block' : 'warning'}`}
          >
            <div>
              <div className="policy-item-name">
                {rule.severity === 'block' ? '🚫' : '⚠️'} {rule.name}
              </div>
              <div className="policy-item-desc">
                {(rule.description || '').trim()}
              </div>
            </div>
            <span className={`policy-badge ${rule.severity === 'block' ? 'block' : 'warning'}`}>
              {rule.severity}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
