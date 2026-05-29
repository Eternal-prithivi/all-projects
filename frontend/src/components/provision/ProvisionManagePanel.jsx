import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api';

const getStatusClass = (status) => {
  if (status === 'deployed') return 'deployed';
  if (['planning', 'applying', 'awaiting_apply'].includes(status)) return 'planning';
  if (status === 'destroyed') return 'destroyed';
  return 'failed';
};

const formatDriftStatus = (s) => {
  if (s === 'clean') return '✓ No drift';
  if (s === 'drift_detected') return '⚠ Drift detected';
  if (s === 'check_failed') return '⚠ Check failed';
  return s || '—';
};

const LOADING_MESSAGES = {
  drift: 'Checking drift against your AWS account… Terraform is comparing live state to your stack. This can take up to a minute.',
  'remediate-preview': 'Running Terraform plan to preview fixes…',
  'remediate-apply': 'Applying Terraform to restore desired state…',
  destroy: 'Destroying infrastructure…',
  detail: 'Loading deployment details…',
};

export default function ProvisionManagePanel({
  userPermissions,
  onDeploymentsChange,
}) {
  const [deployments, setDeployments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);
  const [error, setError] = useState(null);
  const [output, setOutput] = useState('');

  const isBusy = Boolean(loadingAction);

  const loadDeployments = useCallback(async () => {
    try {
      const res = await api.get('/provision/deployments');
      const list = res.data.deployments || [];
      setDeployments(list);
      onDeploymentsChange?.(list.length);
    } catch {
      setDeployments([]);
    }
  }, [onDeploymentsChange]);

  useEffect(() => {
    loadDeployments();
  }, [loadDeployments]);

  const loadDetail = async (deploymentName, { quiet = false } = {}) => {
    setSelectedId(deploymentName);
    if (!quiet) {
      setDetail(null);
      setOutput('');
      setLoadingAction('detail');
    }
    setError(null);
    try {
      const res = await api.get(`/provision/deployments/${deploymentName}`);
      setDetail(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load deployment');
    } finally {
      if (!quiet) {
        setLoadingAction((current) => (current === 'detail' ? null : current));
      }
    }
  };

  const runDriftCheck = async (depId) => {
    setLoadingAction('drift');
    setError(null);
    setOutput('');
    try {
      const res = await api.post(`/provision/deployments/${depId}/drift`);
      setOutput((res.data.details || []).join('\n'));
      await loadDeployments();
      if (selectedId === depId) await loadDetail(depId, { quiet: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Drift check failed');
    } finally {
      setLoadingAction(null);
    }
  };

  const runRemediate = async (depId, checkOnly) => {
    if (!checkOnly && !window.confirm('Run terraform apply to restore desired state?')) return;
    setLoadingAction(checkOnly ? 'remediate-preview' : 'remediate-apply');
    setError(null);
    try {
      const res = await api.post(`/provision/deployments/${depId}/remediate`, { check_only: checkOnly });
      setOutput(res.data.plan_output || res.data.message || '');
      await loadDeployments();
      if (selectedId === depId) await loadDetail(depId, { quiet: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Remediation failed');
    } finally {
      setLoadingAction(null);
    }
  };

  const runDestroy = async (depId) => {
    if (!window.confirm('Destroy this deployment? This cannot be undone.')) return;
    setLoadingAction('destroy');
    setError(null);
    try {
      await api.post(`/provision/destroy/${depId}`);
      setSelectedId(null);
      setDetail(null);
      await loadDeployments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Destroy failed');
    } finally {
      setLoadingAction(null);
    }
  };

  const renderActionSpinner = (label) => (
    <>
      <span className="btn-spinner" aria-hidden="true" />
      {label}
    </>
  );

  if (deployments.length === 0) {
    return (
      <div className="provision-empty-state">
        <h3>No deployments yet</h3>
        <p>
          Use <strong>New stack</strong> to deploy optional Terraform workloads, or focus on
          cost, storage, and VM optimization — your AWS account is already linked in Settings.
        </p>
        <Link to="/dashboard/costs" className="btn-provision secondary" style={{ marginTop: '1rem', display: 'inline-block' }}>
          Open cost analysis →
        </Link>
      </div>
    );
  }

  return (
    <div className="provision-manage-layout">
      {error && (
        <div className="policy-item block" style={{ marginBottom: '1rem' }}>
          <div className="policy-item-desc">{error}</div>
        </div>
      )}

      <div className="provision-manage-grid">
        <div className="deployments-section">
          <h3>Your deployments</h3>
          {deployments.map((dep) => (
            <div
              key={dep._id}
              className={`deployment-card ${selectedId === dep.deployment_name ? 'selected' : ''}${loadingAction === 'drift' && selectedId === dep.deployment_name ? ' card-busy' : ''}`}
              onClick={() => !isBusy && loadDetail(dep.deployment_name)}
              onKeyDown={(e) => e.key === 'Enter' && !isBusy && loadDetail(dep.deployment_name)}
              role="button"
              tabIndex={isBusy ? -1 : 0}
              aria-disabled={isBusy}
            >
              <div className="deployment-info">
                <h4>{dep.deployment_name}</h4>
                <div className="deployment-meta">
                  <span className={`deployment-status ${getStatusClass(dep.status)}`}>
                    {dep.status}
                  </span>
                  {dep.latest_drift && dep.latest_drift !== 'unknown' && (
                    <span className={`drift-indicator ${dep.latest_drift === 'clean' ? 'clean' : 'drift'}`}>
                      {formatDriftStatus(dep.latest_drift)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="provision-detail-panel">
          {loadingAction && (
            <div
              className="provision-action-status"
              role="status"
              aria-live="polite"
              aria-busy="true"
            >
              <div className="provision-spinner" />
              <div>
                <strong>
                  {loadingAction === 'drift' && 'Drift check in progress'}
                  {loadingAction === 'remediate-preview' && 'Previewing fix'}
                  {loadingAction === 'remediate-apply' && 'Applying fix'}
                  {loadingAction === 'destroy' && 'Destroy in progress'}
                  {loadingAction === 'detail' && 'Loading'}
                </strong>
                <p>{LOADING_MESSAGES[loadingAction]}</p>
              </div>
            </div>
          )}

          {!detail && loadingAction !== 'detail' ? (
            <p className="provision-empty-hint">Select a deployment to view drift history and actions.</p>
          ) : !detail ? null : (
            <>
              <h3>{detail.deployment_name}</h3>
              <p className="provision-empty-hint">
                Modules: {(detail.enabled_modules || []).join(', ') || '—'} ·{' '}
                {detail.resources_count || 0} resources
              </p>

              {detail.status === 'deployed' && (
                <div className="provision-actions" style={{ marginTop: '1rem' }}>
                  <button
                    type="button"
                    className={`btn-provision secondary${loadingAction === 'drift' ? ' is-loading' : ''}`}
                    disabled={isBusy}
                    onClick={() => runDriftCheck(detail.deployment_name)}
                  >
                    {loadingAction === 'drift'
                      ? renderActionSpinner('Checking drift…')
                      : 'Check drift'}
                  </button>
                  <button
                    type="button"
                    className={`btn-provision secondary${loadingAction === 'remediate-preview' ? ' is-loading' : ''}`}
                    disabled={isBusy}
                    onClick={() => runRemediate(detail.deployment_name, true)}
                  >
                    {loadingAction === 'remediate-preview'
                      ? renderActionSpinner('Planning…')
                      : 'Preview fix (plan only)'}
                  </button>
                  {detail.latest_drift === 'drift_detected' && (
                    <button
                      type="button"
                      className={`btn-provision primary${loadingAction === 'remediate-apply' ? ' is-loading' : ''}`}
                      disabled={isBusy || (userPermissions && !userPermissions.can_remediate)}
                      onClick={() => runRemediate(detail.deployment_name, false)}
                    >
                      {loadingAction === 'remediate-apply'
                        ? renderActionSpinner('Applying…')
                        : 'Apply fix'}
                    </button>
                  )}
                  <button
                    type="button"
                    className={`btn-provision danger${loadingAction === 'destroy' ? ' is-loading' : ''}`}
                    disabled={isBusy || (userPermissions && !userPermissions.can_destroy)}
                    onClick={() => runDestroy(detail.deployment_name)}
                  >
                    {loadingAction === 'destroy'
                      ? renderActionSpinner('Destroying…')
                      : 'Destroy'}
                  </button>
                </div>
              )}

              <div className="provision-drift-history">
                <h4>Drift history</h4>
                {(detail.drift_history || []).length === 0 ? (
                  <p className="provision-empty-hint">No drift checks yet.</p>
                ) : (
                  <ul>
                    {[...(detail.drift_history || [])].reverse().map((entry, idx) => (
                      <li key={idx}>
                        <strong>{formatDriftStatus(entry.status)}</strong>
                        {entry.checked_at && (
                          <span> · {new Date(entry.checked_at).toLocaleString()}</span>
                        )}
                        {entry.details?.[0] && (
                          <div className="provision-drift-detail">{entry.details[0]}</div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {output && (
                <pre className="provision-output-snippet">{output}</pre>
              )}

              {detail.status === 'deployed' && (
                <Link to="/dashboard/optimization" className="btn-provision secondary" style={{ marginTop: '1rem', display: 'inline-block' }}>
                  Optimize costs for this account →
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
