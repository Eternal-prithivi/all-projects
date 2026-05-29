import React, { useCallback, useEffect, useState } from 'react';
import { FaBuilding, FaUserPlus, FaUsers } from 'react-icons/fa';
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import PageHeader from '../components/ui/PageHeader.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import '../styles/settings.css';
import '../styles/team-page.css';

export default function TeamPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [orgName, setOrgName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/organizations/me');
      setData(res.data);
      setError('');
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load team');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
        role: 'member',
      });
      const link = `${window.location.origin}${res.data.invite_link}`;
      setMessage(`Invite sent. Share link: ${link}`);
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

  if (loading) {
    return <LoadingSpinner size="large" text="Loading team..." />;
  }

  const org = data?.organization;
  const canManage = data?.my_role === 'owner' || data?.my_role === 'admin';

  return (
    <div className="team-page settings-page zenith-page-enter">
      <PageHeader
        kicker="Enterprise"
        title="Team & organization"
        subtitle="Manage members and invites for your workspace"
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

            {canManage && (
              <section className="settings-card zenith-surface animate-fade-in-up">
                <h3>
                  <FaUserPlus aria-hidden />
                  Invite member
                </h3>
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
                  <button type="submit" className="btn-save team-form-row__submit">
                    Send invite
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
              <div className="settings-group">
                {data.members?.map((m) => (
                  <div key={m.username} className="setting-item">
                    <div className="setting-info">
                      <h4>
                        {m.username}
                        {m.username === user?.username && (
                          <span className="team-you-badge">you</span>
                        )}
                      </h4>
                      <p>
                        <span className="team-role-badge">{m.role}</span>
                      </p>
                    </div>
                    {canManage &&
                      m.role !== 'owner' &&
                      m.username !== user?.username && (
                        <button
                          type="button"
                          className="btn-danger-outline team-member-remove"
                          onClick={() => removeMember(m.username)}
                        >
                          Remove
                        </button>
                      )}
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
