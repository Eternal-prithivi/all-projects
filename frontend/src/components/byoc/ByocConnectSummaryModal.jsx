import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BYOC_FEATURE_LABELS } from '../../data/byocCapabilityMatrix';

const FEATURE_ORDER = ['storage', 'security', 'vm', 'provision', 'cost'];

export default function ByocConnectSummaryModal({ data, csp, onClose }) {
  const navigate = useNavigate();
  if (!data) return null;

  const caps = data.capabilities || {};
  const gaps = data.setup_gaps || [];
  const cspLabel = csp === 'GCP' ? 'Google Cloud' : csp === 'Azure' ? 'Azure' : csp;

  const scrollToSetup = () => {
    const anchor = csp === 'GCP' ? 'byoc-gcp-billing' : csp === 'Azure' ? 'byoc-azure-compute' : null;
    onClose();
    if (anchor) {
      navigate(`/dashboard/settings#${anchor}`);
      setTimeout(() => document.getElementById(anchor)?.scrollIntoView({ behavior: 'smooth' }), 100);
    } else {
      navigate('/dashboard/settings');
    }
  };

  return (
    <div className="byoc-summary-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="byoc-summary-title">
      <div className="byoc-summary-modal zenith-surface">
        <h3 id="byoc-summary-title">{cspLabel} connected</h3>
        <p className="byoc-summary-modal__message">{data.message}</p>

        <div className="byoc-summary-matrix" aria-label="Feature readiness">
          {FEATURE_ORDER.map((key) => (
            <span
              key={key}
              className={`byoc-summary-matrix__item ${caps[key] ? 'ready' : 'blocked'}`}
            >
              {BYOC_FEATURE_LABELS[key]}
              {caps[key] ? ' ✓' : ' — blocked'}
            </span>
          ))}
        </div>

        {(data.unlocked_features || []).includes('storage') && (
          <p className="byoc-summary-modal__ready">
            Storage and Security are ready. You can upload files now.
          </p>
        )}

        {gaps.length > 0 && (
          <div className="byoc-summary-modal__gaps">
            <strong>Complete later to unlock more:</strong>
            <ul>
              {gaps.map((g) => (
                <li key={g.code}>{g.message}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="byoc-summary-modal__actions">
          <Link to="/dashboard/storage" className="btn-connect-save" onClick={onClose}>
            Go to Storage
          </Link>
          {gaps.length > 0 && (
            <button type="button" className="btn-secondary" onClick={scrollToSetup}>
              Complete setup in Settings
            </button>
          )}
          <button type="button" className="btn-secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
