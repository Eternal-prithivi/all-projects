import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api';
import PageHeader from '../components/ui/PageHeader.jsx';
import { useAuth } from '../context/AuthContext.jsx';
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
    try {
      await apiClient.delete(`/organizations/members/${username}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not remove member');
    }
  };

  const leaveOrg = async () => {
    if (!window.confirm('Leave this organization?')) return;
    try {
      await apiClient.post('/organizations/leave');
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not leave organization');
    }
  };

  if (loading) {
    return <p className="team-page__loading">Loading team…</p>;
  }

  const org = data?.organization;

  return (
    <div className="team-page zenith-page-enter">
      <PageHeader
        kicker="Enterprise"
        title="Team & organization"
        subtitle="Manage members and invites for your workspace"
      />

      {message && <p className="team-page__success">{message}</p>}
      {error && <p className="team-page__error">{error}</p>}

      {!org ? (
        <section className="team-card">
          <h2>Create your organization</h2>
          <p>Start a team workspace and invite colleagues by email.</p>
          <form onSubmit={createOrg} className="team-form">
            <input
              type="text"
              placeholder="Organization name"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
              minLength={2}
            />
            <button type="submit" className="btn-primary">
              Create organization
            </button>
          </form>
        </section>
      ) : (
        <>
          <section className="team-card">
            <div className="team-card__header">
              <div>
                <h2>{org.name}</h2>
                <p>
                  Your role: <strong>{data.my_role}</strong> · Owner: {org.owner_username}
                </p>
              </div>
              <button type="button" className="btn-secondary" onClick={leaveOrg}>
                Leave organization
              </button>
            </div>
          </section>

          {(data.my_role === 'owner' || data.my_role === 'admin') && (
            <section className="team-card">
              <h3>Invite member</h3>
              <form onSubmit={sendInvite} className="team-form">
                <input
                  type="email"
                  placeholder="colleague@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                />
                <button type="submit" className="btn-primary">
                  Send invite
                </button>
              </form>
              {data.pending_invites?.length > 0 && (
                <ul className="team-invites">
                  {data.pending_invites.map((inv) => (
                    <li key={inv.email}>
                      {inv.email} — {inv.role} (expires{' '}
                      {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : 'soon'})
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          <section className="team-card">
            <h3>Members ({data.members?.length || 0})</h3>
            <ul className="team-members">
              {data.members?.map((m) => (
                <li key={m.username}>
                  <span>
                    {m.username}
                    {m.username === user?.username && ' (you)'}
                  </span>
                  <span className="team-members__role">{m.role}</span>
                  {(data.my_role === 'owner' || data.my_role === 'admin') &&
                    m.role !== 'owner' &&
                    m.username !== user?.username && (
                      <button type="button" onClick={() => removeMember(m.username)}>
                        Remove
                      </button>
                    )}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
