import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaBuilding,
  FaCheckCircle,
  FaClock,
  FaUserPlus,
  FaUsers,
  FaDollarSign,
  FaServer,
  FaHdd,
} from 'react-icons/fa';
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import PageHeader from '../components/ui/PageHeader.jsx';
import SparklineChart from '../components/dashboard/SparklineChart.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import { useAuth } from '../context/AuthContext.jsx';
import { NOT_YET_AVAILABLE, PATHS, TEAM_CAPABILITIES } from '../data/productFacts.js';
import { usePlanEntitlementsContext } from '../context/PlanEntitlementsContext.jsx';
import PlanUpgradeGate from '../components/billing/PlanUpgradeGate.jsx';
import { NAV_ID_LABELS, MIN_PLAN_LABELS } from '../config/planNavConfig.js';
import '../styles/settings.css';
import '../styles/billing.css';
import '../styles/team-page.css';

const ONBOARDING_KEY = 'zenith_team_onboarding_dismissed';

export default function TeamPage() {
  const { user } = useAuth();
  const { isFeatureEnabled, planName, getNavMeta } = usePlanEntitlementsContext();
  const [data, setData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [recommendations, setRecommendations] = useState({ items: [] });
  const [approvals, setApprovals] = useState({ approvals: [] });
  const [loading, setLoading] = useState(true);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const [orgName, setOrgName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [lastInviteLink, setLastInviteLink] = useState('');
  const [budgetUsd, setBudgetUsd] = useState('');
  const [approvalThreshold, setApprovalThreshold] = useState('');
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [orgBilling, setOrgBilling] = useState(null);
  const [resourceSummary, setResourceSummary] = useState(null);
  const [memberCloudStatus, setMemberCloudStatus] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const meRes = await apiClient.get('/organizations/me');
      setData(meRes.data);
      setError('');

      if (meRes.data?.organization) {
        const [sumRes, recRes, appRes, billRes, resRes, cloudRes] = await Promise.allSettled([
          apiClient.get('/organizations/summary'),
          apiClient.get('/organizations/recommendations'),
          apiClient.get('/organizations/approvals?status=pending'),
          apiClient.get('/organizations/billing'),
          apiClient.get('/organizations/resources/summary'),
          apiClient.get('/organizations/members/cloud-status'),
        ]);
        if (sumRes.status === 'fulfilled') {
          setSummary(sumRes.value.data);
          setBudgetUsd(
            sumRes.value.data?.monthly_budget_usd != null
              ? String(sumRes.value.data.monthly_budget_usd)
              : ''
          );
          setApprovalThreshold(
            sumRes.value.data?.approval_threshold_usd != null
              ? String(sumRes.value.data.approval_threshold_usd)
              : ''
          );
        }
        if (recRes.status === 'fulfilled') setRecommendations(recRes.value.data);
        if (appRes.status === 'fulfilled') setApprovals(appRes.value.data);
        if (billRes.status === 'fulfilled') setOrgBilling(billRes.value.data);
        else setOrgBilling(null);
        if (resRes.status === 'fulfilled') setResourceSummary(resRes.value.data);
        else setResourceSummary(null);
        if (cloudRes.status === 'fulfilled') {
          setMemberCloudStatus(cloudRes.value.data?.members || []);
        } else {
          setMemberCloudStatus([]);
        }
      } else {
        setSummary(null);
        setRecommendations({ items: [] });
        setApprovals({ approvals: [] });
        setOrgBilling(null);
        setResourceSummary(null);
        setMemberCloudStatus([]);
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load team');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!user?.username) return;
    const dismissed = localStorage.getItem(`${ONBOARDING_KEY}_${user.username}`);
    if (!dismissed && data?.organization && data?.my_role === 'member') {
      const joined = data.members?.find((m) => m.username === user.username)?.joined_at;
      if (joined) {
        const days = (Date.now() - new Date(joined).getTime()) / 86400000;
        setShowOnboarding(days <= 14);
      }
    }
  }, [data, user]);

  const dismissOnboarding = () => {
    if (user?.username) {
      localStorage.setItem(`${ONBOARDING_KEY}_${user.username}`, '1');
    }
    setShowOnboarding(false);
  };

  const createOrg = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    try {
      await apiClient.post('/organizations', { name: orgName });
      setMessage('Organization created');
      setOrgName('');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create organization');
    }
  };

  const sendInvite = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    try {
      const res = await apiClient.post('/organizations/invites', {
        email: inviteEmail,
        role: inviteRole,
      });
      const link = `${window.location.origin}${res.data.invite_link}`;
      setLastInviteLink(link);
      setMessage(
        res.data.email_sent
          ? 'Invite created and emailed. You can also copy the link below.'
          : 'Invite created. Copy the link below to share (email not configured).'
      );
      setInviteEmail('');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not send invite');
    }
  };

  const removeMember = async (username) => {
    if (!window.confirm(`Remove ${username} from the team?`)) return;
    setMessage('');
    try {
      await apiClient.delete(`/organizations/members/${username}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not remove member');
    }
  };

  const copyInviteLink = async () => {
    if (!lastInviteLink) return;
    try {
      await navigator.clipboard.writeText(lastInviteLink);
      setMessage('Invite link copied to clipboard');
    } catch {
      setError('Could not copy link — select and copy manually');
    }
  };

  const revokeInvite = async (email) => {
    if (!window.confirm(`Revoke invite for ${email}?`)) return;
    setMessage('');
    try {
      await apiClient.delete(`/organizations/invites/${encodeURIComponent(email)}`);
      setMessage(`Revoked invite for ${email}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not revoke invite');
    }
  };

  const leaveOrg = async () => {
    if (!window.confirm('Leave this organization?')) return;
    setMessage('');
    try {
      await apiClient.post('/organizations/leave');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not leave organization');
    }
  };

  const changeRole = async (username, role) => {
    setMessage('');
    try {
      await apiClient.patch(`/organizations/members/${username}/role`, { role });
      setMessage(`Updated role for ${username}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update role');
    }
  };

  const migratePersonalBilling = async () => {
    if (!window.confirm('Move your personal subscription to this organization? This cannot be undone.')) return;
    setMessage('');
    try {
      await apiClient.post('/organizations/billing/migrate-personal');
      setMessage('Personal subscription moved to organization');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not migrate subscription');
    }
  };

  const transferOwnership = async (username) => {
    if (!window.confirm(`Transfer ownership to ${username}? You will become an admin.`)) return;
    setMessage('');
    try {
      await apiClient.post('/organizations/transfer-ownership', {
        new_owner_username: username,
      });
      setMessage(`Ownership transferred to ${username}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not transfer ownership');
    }
  };

  const saveSettings = async (e) => {
    e.preventDefault();
    setMessage('');
    try {
      const payload = {};
      if (budgetUsd !== '') payload.monthly_budget_usd = parseFloat(budgetUsd) || 0;
      if (approvalThreshold !== '') {
        payload.approval_threshold_usd = parseFloat(approvalThreshold) || 0;
      }
      await apiClient.patch('/organizations/settings', payload);
      setMessage('Organization settings saved');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save settings');
    }
  };

  const reviewApproval = async (id, status) => {
    setMessage('');
    try {
      await apiClient.patch(`/organizations/approvals/${id}`, { status });
      setMessage(`Request ${status}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not review approval');
    }
  };

  const sparklineData = useMemo(() => {
    if (!summary?.trend?.has_data) return [];
    return (summary.trend.points || []).map((p) => ({ name: p.label, value: p.value }));
  }, [summary]);

  if (loading) {
    return <LoadingSpinner size="large" text="Loading team..." />;
  }

  const org = data?.organization;
  const canManage = data?.my_role === 'owner' || data?.my_role === 'admin';
  const isOwner = data?.my_role === 'owner';
  const canViewSpend = summary?.can_view_member_spend;
  const totals = summary?.org_totals;

  return (
    <div className="team-page settings-page zenith-page-enter">
      <PageHeader
        kicker="Enterprise"
        title="Team & organization"
        subtitle="Manage members, team cloud health, and governance"
        actions={
          org ? (
            <Link to={PATHS.billing} className="btn-save team-page__header-link">
              View billing
            </Link>
          ) : null
        }
        onRefresh={() =>
          runPageRefresh(load, {
            loadingMessage: 'Refreshing team page…',
            successMessage: 'Team page refreshed.',
            errorMessage: 'Failed to refresh team page.',
          })
        }
        refreshing={pageRefreshing || loading}
      />

      {message && (
        <p className="team-page__alert team-page__alert--success" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="team-page__alert team-page__alert--error" role="alert">
          {error}
        </p>
      )}

      <section className="team-capability-card zenith-surface">
        <h3 className="team-capability-card__title">What teams can do</h3>
        <div className="team-capability-grid">
          <div>
            <p className="team-capability-card__label">
              <FaCheckCircle aria-hidden /> Today
            </p>
            <ul className="team-capability-list">
              {TEAM_CAPABILITIES.today.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="team-capability-card__label team-capability-card__label--muted">
              <FaClock aria-hidden /> Coming soon
            </p>
            <ul className="team-capability-list team-capability-list--muted">
              {TEAM_CAPABILITIES.comingSoon.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
        <p className="team-page__billing-honesty">{NOT_YET_AVAILABLE.orgBilling}</p>
      </section>

      {orgBilling && (
        <section className="team-seats-card zenith-surface">
          <h3>Organization plan &amp; seats</h3>
          <p className="team-page__meta">
            <span className="team-role-badge">{orgBilling.plan_name || orgBilling.plan_id}</span>
            <span className="team-page__meta-sep">·</span>
            {orgBilling.seats_used} / {orgBilling.seat_count} seats used
            {orgBilling.seats_available === 0 && ' — full'}
          </p>
          {orgBilling.current_period_end && (
            <p className="team-field-hint">
              Renews {new Date(orgBilling.current_period_end).toLocaleDateString()}
            </p>
          )}
          <div className="team-seats-card__actions">
            {orgBilling.can_manage_billing && !isFeatureEnabled('team_seat_billing') && orgBilling.plan_id === 'free' ? (
              <PlanUpgradeGate
                featureLabel={NAV_ID_LABELS.team_seat_billing}
                currentPlan={planName}
                requiredPlan={MIN_PLAN_LABELS[getNavMeta('team_seat_billing')?.min_plan] || 'Pro'}
                requiredPlanId={getNavMeta('team_seat_billing')?.min_plan || 'pro'}
                compact
              />
            ) : null}
            {orgBilling.can_manage_billing && (isFeatureEnabled('team_seat_billing') || orgBilling.plan_id !== 'free') && (
              <>
                <Link to={PATHS.billing} className="btn-save team-page__header-link">
                  Manage org billing
                </Link>
                {isOwner && orgBilling.plan_id === 'free' && isFeatureEnabled('team_seat_billing') && (
                  <button type="button" className="btn-save" onClick={migratePersonalBilling}>
                    Move personal plan here
                  </button>
                )}
              </>
            )}
            {!orgBilling.can_manage_billing && (
              <p className="team-field-hint">Contact your org admin to change plan or add seats.</p>
            )}
          </div>
        </section>
      )}

      {resourceSummary && (
        <section className="team-seats-card zenith-surface">
          <h3>Organization resources</h3>
          <p className="team-page__meta">
            {resourceSummary.total_vms} VMs · {resourceSummary.total_storage_gb} GB storage
          </p>
        </section>
      )}

      {showOnboarding && (
        <section className="team-onboarding-card zenith-surface">
          <h3>Welcome to the team</h3>
          <ol className="team-onboarding-list">
            <li>Connect your cloud provider in Settings</li>
            <li>
              Open <Link to={PATHS.dashboard}>Overview</Link> and refresh costs
            </li>
            <li>
              Review <Link to={PATHS.costs}>Cost Analysis</Link> for savings opportunities
            </li>
          </ol>
          <button type="button" className="btn-save" onClick={dismissOnboarding}>
            Got it
          </button>
        </section>
      )}

      {lastInviteLink && (
        <div className="team-page__invite-copy">
          <code>{lastInviteLink}</code>
          <button type="button" className="btn-save" onClick={copyInviteLink}>
            Copy invite link
          </button>
        </div>
      )}

      <div className="settings-content stagger-children">
        {!org ? (
          <section className="settings-card zenith-surface animate-fade-in-up">
            <h3>
              <FaBuilding aria-hidden />
              Create your organization
            </h3>
            <p className="team-page__intro">
              Start a team workspace and invite colleagues by email. Each account can belong to one
              organization at a time.
            </p>
            <form onSubmit={createOrg} className="settings-group">
              <div className="setting-item-full">
                <label htmlFor="team-org-name">Organization name</label>
                <input
                  id="team-org-name"
                  type="text"
                  className="form-input team-page__input"
                  placeholder="Acme Cloud Ops"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                  minLength={2}
                  autoComplete="organization"
                />
              </div>
              <button type="submit" className="btn-save">
                Create organization
              </button>
            </form>
          </section>
        ) : (
          <>
            <section className="settings-card zenith-surface animate-fade-in-up">
              <div className="team-org-header">
                <div>
                  <h3>
                    <FaBuilding aria-hidden />
                    {org.name}
                  </h3>
                  <p className="team-page__meta">
                    Your role: <span className="team-role-badge">{data.my_role}</span>
                    <span className="team-page__meta-sep">·</span>
                    Owner: {org.owner_username}
                  </p>
                </div>
                <button type="button" className="btn-danger-outline" onClick={leaveOrg}>
                  Leave organization
                </button>
              </div>
            </section>

            {summary && totals && (
              <>
                <div className="billing-metrics team-metrics-row">
                  <div className="billing-metric-card">
                    <FaUsers className="team-metric-icon" aria-hidden />
                    <span className="billing-metric-label">Members</span>
                    <span className="billing-metric-value">{totals.member_count}</span>
                  </div>
                  <div className="billing-metric-card">
                    <FaDollarSign className="team-metric-icon" aria-hidden />
                    <span className="billing-metric-label">Org monthly spend</span>
                    <span className="billing-metric-value">
                      ${totals.monthly_spend_usd?.toLocaleString(undefined, { minimumFractionDigits: 2 }) ?? '0.00'}
                    </span>
                  </div>
                  <div className="billing-metric-card">
                    <FaServer className="team-metric-icon" aria-hidden />
                    <span className="billing-metric-label">Total VMs</span>
                    <span className="billing-metric-value">{totals.total_vms}</span>
                  </div>
                  <div className="billing-metric-card">
                    <FaHdd className="team-metric-icon" aria-hidden />
                    <span className="billing-metric-label">Storage</span>
                    <span className="billing-metric-value">{totals.total_storage_gb} GB</span>
                  </div>
                </div>

                {sparklineData.length > 0 && (
                  <section className="settings-card zenith-surface team-sparkline-card">
                    <h3>7-day team spend trend</h3>
                    <SparklineChart data={sparklineData} height={100} />
                    {!summary.has_cost_data && (
                      <p className="team-empty-hint">
                        No snapshot data yet — members should open{' '}
                        <Link to={PATHS.dashboard}>Overview</Link> and click Refresh.
                      </p>
                    )}
                  </section>
                )}

                {summary.monthly_budget_usd != null && summary.monthly_budget_usd > 0 && (
                  <section className="settings-card zenith-surface">
                    <h3>Org budget</h3>
                    <div className="team-budget-progress">
                      <div
                        className={`budget-progress-bar team-budget-bar team-budget-bar--${summary.budget_status || 'ok'}`}
                        style={{ width: `${Math.min(summary.budget_used_percent || 0, 100)}%` }}
                      />
                    </div>
                    <p className="team-page__meta">
                      ${totals.monthly_spend_usd?.toFixed(2)} of ${summary.monthly_budget_usd?.toFixed(2)} (
                      {summary.budget_used_percent ?? 0}%)
                      {summary.budget_status === 'exceeded' && ' — over budget'}
                      {summary.budget_status === 'warning' && ' — approaching limit'}
                    </p>
                  </section>
                )}
              </>
            )}

            {canManage && (
              <section className="settings-card zenith-surface animate-fade-in-up">
                <h3>Organization settings</h3>
                <form onSubmit={saveSettings} className="team-settings-form">
                  <div className="setting-item-full">
                    <label htmlFor="team-budget">Monthly org budget (USD)</label>
                    <input
                      id="team-budget"
                      type="number"
                      min="0"
                      step="1"
                      className="form-input team-page__input"
                      placeholder="e.g. 500"
                      value={budgetUsd}
                      onChange={(e) => setBudgetUsd(e.target.value)}
                    />
                  </div>
                  <div className="setting-item-full">
                    <label htmlFor="team-approval-threshold">
                      Provision approval threshold (USD/mo)
                    </label>
                    <input
                      id="team-approval-threshold"
                      type="number"
                      min="0"
                      step="1"
                      className="form-input team-page__input"
                      placeholder="e.g. 100"
                      value={approvalThreshold}
                      onChange={(e) => setApprovalThreshold(e.target.value)}
                    />
                    <p className="team-field-hint">
                      Members must get admin approval before planning deployments above this estimate.
                    </p>
                  </div>
                  <button type="submit" className="btn-save">
                    Save settings
                  </button>
                </form>
              </section>
            )}

            {recommendations.items?.length > 0 && (
              <section className="settings-card zenith-surface">
                <h3>Team actions</h3>
                <ul className="team-actions-list">
                  {recommendations.items.map((item) => (
                    <li key={item.id} className={`team-action-item team-action-item--${item.severity}`}>
                      <span>{item.message}</span>
                      {item.action_path && (
                        <Link to={item.action_path} className="team-action-link">
                          View →
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(canManage || approvals.approvals?.length > 0) && (
              <section className="settings-card zenith-surface">
                <h3>Pending approvals</h3>
                {approvals.approvals?.length === 0 ? (
                  <p className="team-page__meta">No pending provision approvals.</p>
                ) : (
                  <ul className="team-actions-list">
                    {approvals.approvals.map((a) => (
                      <li key={a.id} className="team-action-item">
                        <span>
                          {a.requester}: {a.payload_summary || a.type} — est. $
                          {a.estimated_monthly_usd?.toFixed(2)}/mo
                        </span>
                        {canManage && (
                          <span className="team-approval-btns">
                            <button
                              type="button"
                              className="btn-save"
                              onClick={() => reviewApproval(a.id, 'approved')}
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className="btn-danger-outline"
                              onClick={() => reviewApproval(a.id, 'denied')}
                            >
                              Deny
                            </button>
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}

            {canManage && (
              <section className="settings-card zenith-surface animate-fade-in-up">
                <h3>
                  <FaUserPlus aria-hidden />
                  Invite member
                </h3>
                <p className="team-field-hint team-invite-hint">
                  We&apos;ll email a link if SMTP is configured; you can always copy the link too.
                </p>
                <form onSubmit={sendInvite} className="team-form-row">
                  <div className="setting-item-full team-form-row__field">
                    <label htmlFor="team-invite-email" className="visually-hidden">
                      Email address
                    </label>
                    <input
                      id="team-invite-email"
                      type="email"
                      className="form-input team-page__input"
                      placeholder="colleague@company.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                      autoComplete="email"
                    />
                  </div>
                  <div className="team-form-row__role">
                    <label htmlFor="team-invite-role" className="visually-hidden">
                      Role
                    </label>
                    <select
                      id="team-invite-role"
                      className="form-input team-page__input"
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value)}
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  <button type="submit" className="btn-save team-form-row__submit">
                    Create invite
                  </button>
                </form>
                {data.pending_invites?.length > 0 && (
                  <div className="settings-group team-pending-invites">
                    <p className="team-pending-invites__label">Pending invites</p>
                    {data.pending_invites.map((inv) => (
                      <div key={inv.email} className="setting-item team-pending-invites__item">
                        <div className="setting-info">
                          <h4>{inv.email}</h4>
                          <p>
                            {inv.role} · expires{' '}
                            {inv.expires_at
                              ? new Date(inv.expires_at).toLocaleDateString()
                              : 'soon'}
                          </p>
                        </div>
                        <button
                          type="button"
                          className="btn-danger-outline"
                          onClick={() => revokeInvite(inv.email)}
                        >
                          Revoke
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            <section className="settings-card zenith-surface animate-fade-in-up">
              <h3>
                <FaUsers aria-hidden />
                Members ({data.members?.length || 0})
              </h3>
              <div className="team-member-table">
                <div className="team-member-table__head">
                  <span>Member</span>
                  <span>Role</span>
                  {memberCloudStatus.length > 0 && <span>Cloud</span>}
                  {summary && <span>VMs</span>}
                  {summary && <span>Storage</span>}
                  {summary && <span>Spend/mo</span>}
                  <span>Joined</span>
                  <span />
                </div>
                {(summary?.members || data.members)?.map((m) => {
                  const showStats = canViewSpend || m.username === user?.username;
                  const cloudRow = memberCloudStatus.find((c) => c.username === m.username);
                  const cloudLabel = cloudRow?.cloud_summary
                    ? Object.entries(cloudRow.cloud_summary)
                        .filter(([, v]) => v !== 'not connected')
                        .map(([csp, v]) => `${csp}: ${v}`)
                        .join(' · ') || '—'
                    : '—';
                  return (
                    <div key={m.username} className="team-member-table__row">
                      <span>
                        {m.username}
                        {m.username === user?.username && (
                          <span className="team-you-badge">you</span>
                        )}
                      </span>
                      <span>
                        {isOwner && m.role !== 'owner' && m.username !== user?.username ? (
                          <select
                            className="team-role-select"
                            value={m.role}
                            onChange={(e) => changeRole(m.username, e.target.value)}
                          >
                            <option value="admin">admin</option>
                            <option value="member">member</option>
                          </select>
                        ) : (
                          <span className="team-role-badge">{m.role}</span>
                        )}
                      </span>
                      {memberCloudStatus.length > 0 && (
                        <span className="team-cloud-cell" title="Each member manages BYOC in their own Settings">
                          {cloudLabel}
                        </span>
                      )}
                      {summary && (
                        <span>{showStats ? m.vm_count ?? '—' : '—'}</span>
                      )}
                      {summary && (
                        <span>{showStats ? `${m.storage_gb ?? 0} GB` : '—'}</span>
                      )}
                      {summary && (
                        <span>
                          {showStats
                            ? `$${(m.monthly_spend_usd ?? 0).toFixed(2)}`
                            : '—'}
                        </span>
                      )}
                      <span>
                        {m.joined_at
                          ? new Date(m.joined_at).toLocaleDateString()
                          : '—'}
                      </span>
                      <span className="team-member-actions">
                        {isOwner &&
                          m.role !== 'owner' &&
                          m.username !== user?.username && (
                            <button
                              type="button"
                              className="btn-save team-transfer-btn"
                              onClick={() => transferOwnership(m.username)}
                            >
                              Make owner
                            </button>
                          )}
                        {canManage &&
                          m.role !== 'owner' &&
                          m.username !== user?.username &&
                          ((m.vm_count ?? 0) > 0 || (m.storage_gb ?? 0) > 0 ? (
                            <span
                              className="team-field-hint"
                              title="Reassign or delete their VMs and files before removing"
                            >
                              Has resources
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="btn-danger-outline"
                              onClick={() => removeMember(m.username)}
                            >
                              Remove
                            </button>
                          ))}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
