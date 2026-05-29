import React, { useCallback, useEffect, useState } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import PageHeader from '../../components/ui/PageHeader.jsx';
import '../../styles/admin-pages.css';
import '../../styles/provision.css';

const ROLES = ['viewer', 'developer', 'devops', 'admin'];

export default function AdminProvisionRolesPage() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('developer');
  const [saving, setSaving] = useState(false);

  const loadRoles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/provision/roles');
      setAssignments(res.data.assignments || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load provision roles');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoles();
  }, [loadRoles]);

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!username.trim()) return;
    setSaving(true);
    try {
      await api.post('/provision/roles/assign', { username: username.trim(), role });
      toast.success(`Provision role "${role}" assigned to ${username.trim()}`);
      setUsername('');
      loadRoles();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to assign role');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-page">
      <PageHeader
        kicker="Admin"
        title="Provision roles"
        subtitle="Who can plan, apply, destroy, and remediate Terraform stacks. AWS connection stays in user Settings."
      />

      <form className="admin-form-card provision-rbac-form" onSubmit={handleAssign}>
        <h3>Assign role</h3>
        <div className="config-form" style={{ gridTemplateColumns: '1fr 1fr auto' }}>
          <div className="config-field">
            <label htmlFor="prov-username">Username</label>
            <input
              id="prov-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="zenith_user"
            />
          </div>
          <div className="config-field">
            <label htmlFor="prov-role">Provision role</label>
            <select
              id="prov-role"
              className="zenith-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn-provision primary" disabled={saving} style={{ alignSelf: 'end' }}>
            {saving ? 'Saving…' : 'Assign'}
          </button>
        </div>
      </form>

      <div className="admin-table-card" style={{ marginTop: '1.5rem' }}>
        <h3>Current assignments</h3>
        {loading ? (
          <p>Loading…</p>
        ) : assignments.length === 0 ? (
          <p className="provision-empty-hint">No explicit roles — users default to developer (Zenith admins get provision admin).</p>
        ) : (
          <table className="cost-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Assigned by</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((a) => (
                <tr key={a.username}>
                  <td>{a.username}</td>
                  <td>{a.role}</td>
                  <td>{a.assigned_by || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
