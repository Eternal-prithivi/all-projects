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

const formatWhen = (dep) => {
  const raw = dep.archived_at || dep.created_at || dep.updated_at;
  if (!raw) return '';
  try {
    return new Date(raw).toLocaleString();
  } catch {
    return '';
  }
};

const LOADING_MESSAGES = {
  drift: 'Checking drift against your AWS account… Terraform is comparing live state to your stack. This can take up to a minute.',
  'remediate-preview': 'Running Terraform plan to preview fixes…',
  'remediate-apply': 'Applying Terraform to restore desired state…',
  destroy: 'Destroying infrastructure…',
  detail: 'Loading deployment details…',
  delete: 'Updating deployment list…',
};

function DeploymentRow({
  dep,
  selectedId,
  isBusy,
  muted,
  deleteLabel,
  onSelect,
  onDelete,
}) {
  return (
    <div
      className={`deployment-card ${selectedId === dep.deployment_name ? 'selected' : ''}${muted ? ' deployment-card--history' : ''}`}
      onClick={() => !isBusy && onSelect(dep.deployment_name)}
      onKeyDown={(e) => e.key === 'Enter' && !isBusy && onSelect(dep.deployment_name)}
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
          {dep.template && <span className="deployment-tag">{dep.template}</span>}
          {formatWhen(dep) && <span className="deployment-when">{formatWhen(dep)}</span>}
          {!muted && dep.latest_drift && dep.latest_drift !== 'unknown' && (
            <span className={`drift-indicator ${dep.latest_drift === 'clean' ? 'clean' : 'drift'}`}>
              {formatDriftStatus(dep.latest_drift)}
            </span>
          )}
        </div>
      </div>
      <button
        type="button"
        className="deployment-delete-btn"
        title={deleteLabel}
        disabled={isBusy}
        onClick={(e) => onDelete(e, dep)}
      >
        {deleteLabel}
      </button>
    </div>
  );
}

export default function ProvisionManagePanel({ onDeploymentsChange }) {
  const [recent, setRecent] = useState([]);
  const [history, setHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);
  const [error, setError] = useState(null);
  const [output, setOutput] = useState('');

  const isBusy = Boolean(loadingAction);

  const loadDeployments = useCallback(async () => {
    try {
      const res = await api.get('/provision/deployments');
      const recentList = res.data.recent || res.data.deployments || [];
      const historyList = res.data.history || [];
      setRecent(recentList);
      setHistory(historyList);
      onDeploymentsChange?.(recentList.length);
    } catch {
      setRecent([]);
      setHistory([]);
      onDeploymentsChange?.(0);
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

  const archiveDeployment = async (e, dep) => {
    e.stopPropagation();
    const isLive = dep.status === 'deployed';
    const msg = isLive
      ? 'Archive this deployment? AWS resources are NOT removed — open it and use Destroy first if you want to tear down infrastructure.'
      : 'Remove this from recent deployments? It will move to history.';
    if (!window.confirm(msg)) return;

    setLoadingAction('delete');
    setError(null);
    try {
      await api.delete(`/provision/deployments/${dep.deployment_name}`);
      if (selectedId === dep.deployment_name) {
        setSelectedId(null);
        setDetail(null);
      }
      await loadDeployments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not archive deployment');
    } finally {
      setLoadingAction(null);
    }
  };

  const permanentlyRemove = async (e, dep) => {
    e.stopPropagation();
    if (!window.confirm('Permanently delete this record from history? This cannot be undone.')) {
      return;
    }

    setLoadingAction('delete');
    setError(null);
    try {
      await api.delete(`/provision/deployments/${dep.deployment_name}?permanent=true`);
      if (selectedId === dep.deployment_name) {
        setSelectedId(null);
        setDetail(null);
      }
      await loadDeployments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete record');
    } finally {
      setLoadingAction(null);
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

  const hasAny = recent.length > 0 || history.length > 0;

  if (!hasAny) {
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
          <div className="deployments-section-header">
            <h3>Recent deployments</h3>
            <span className="deployments-section-hint">Last {recent.length} active</span>
          </div>

          {recent.length === 0 ? (
            <p className="provision-empty-hint">
              No recent deployments. Open history below or create a new stack.
            </p>
          ) : (
            recent.map((dep) => (
              <DeploymentRow
                key={dep._id || dep.deployment_name}
                dep={dep}
                selectedId={selectedId}
                isBusy={isBusy}
                muted={false}
                deleteLabel="Archive"
                onSelect={loadDetail}
                onDelete={archiveDeployment}
              />
            ))
          )}

          {history.length > 0 && (
            <div className="deployments-history-block">
              <button
                type="button"
                className="deployments-history-toggle"
                onClick={() => setHistoryOpen((o) => !o)}
                aria-expanded={historyOpen}
              >
                {historyOpen ? '▼' : '▶'} History ({history.length})
              </button>
              {historyOpen && (
                <div className="deployments-history-list">
                  <p className="provision-empty-hint deployments-history-note">
                    Archived stacks and older runs. Remove clears the record only (not AWS).
                  </p>
                  {history.map((dep) => (
                    <DeploymentRow
                      key={dep._id || dep.deployment_name}
                      dep={dep}
                      selectedId={selectedId}
                      isBusy={isBusy}
                      muted
                      deleteLabel={dep.archived ? 'Remove' : 'Archive'}
                      onSelect={loadDetail}
                      onDelete={dep.archived ? permanentlyRemove : archiveDeployment}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
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
                  {loadingAction === 'delete' && 'Updating list'}
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
                      disabled={isBusy}
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
                    disabled={isBusy}
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
