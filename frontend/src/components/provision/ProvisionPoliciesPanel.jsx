import React, { useCallback, useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../../api';

const EMPTY_FORM = {
  name: '',
  description: '',
  severity: 'warning',
  condition: '',
};

const CONDITION_HINTS = [
  { label: 'Require tags', value: "tags is None or tags == {}" },
  { label: 'Block non-micro instances', value: "instance_type not in ['t2.micro', 't3.micro', 't4g.micro']" },
  { label: 'High budget warning', value: 'budget_limit is not None and int(budget_limit) > 10' },
];

export default function ProvisionPoliciesPanel() {
  const [rules, setRules] = useState([]);
  const [counts, setCounts] = useState({ builtin: 0, custom: 0, override: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  const loadRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/provision/policy-rules');
      setRules(res.data.rules || []);
      setCounts({
        builtin: res.data.builtin_count ?? 0,
        custom: res.data.custom_count ?? 0,
        override: res.data.override_count ?? 0,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load policies'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const openCreate = () => {
    setEditing({ mode: 'custom' });
    setForm(EMPTY_FORM);
    setFormError(null);
    setShowForm(true);
  };

  const openEditCustom = (rule) => {
    setEditing({ mode: 'custom', id: rule.id, source: 'custom' });
    setForm({
      name: rule.name,
      description: (rule.description || '').trim(),
      severity: rule.severity,
      condition: rule.condition || '',
    });
    setFormError(null);
    setShowForm(true);
  };

  const openCustomizeBuiltin = (rule) => {
    setEditing({ mode: 'builtin', name: rule.name, source: rule.source });
    setForm({
      name: rule.name,
      description: (rule.description || '').trim(),
      severity: rule.severity,
      condition: rule.condition || '',
    });
    setFormError(null);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      if (editing?.mode === 'builtin') {
        await api.put(`/provision/policy-rules/builtin/${editing.name}`, {
          description: form.description,
          severity: form.severity,
          condition: form.condition,
          enabled: true,
        });
      } else if (editing?.id) {
        await api.put(`/provision/policy-rules/custom/${editing.id}`, form);
      } else {
        await api.post('/provision/policy-rules/custom', form);
      }
      closeForm();
      await loadRules();
    } catch (err) {
      setFormError(getApiErrorMessage(err, 'Could not save policy'));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleCustom = async (rule) => {
    try {
      await api.put(`/provision/policy-rules/custom/${rule.id}`, {
        enabled: !rule.enabled,
      });
      await loadRules();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to update policy'));
    }
  };

  const handleDisableBuiltin = async (rule) => {
    try {
      await api.put(`/provision/policy-rules/builtin/${rule.name}`, { enabled: false });
      await loadRules();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to disable policy'));
    }
  };

  const handleEnableBuiltin = async (rule) => {
    try {
      await api.put(`/provision/policy-rules/builtin/${rule.name}`, { enabled: true });
      await loadRules();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to enable policy'));
    }
  };

  const handleResetBuiltin = async (rule) => {
    if (!window.confirm(`Reset "${rule.name}" to platform default?`)) return;
    try {
      await api.delete(`/provision/policy-rules/builtin/${rule.name}`);
      await loadRules();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to reset policy'));
    }
  };

  const handleDeleteCustom = async (rule) => {
    if (!window.confirm(`Delete custom policy "${rule.name}"?`)) return;
    try {
      await api.delete(`/provision/policy-rules/custom/${rule.id}`);
      await loadRules();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to delete policy'));
    }
  };

  const platformRules = rules.filter((r) => r.source === 'builtin' || r.source === 'override');
  const customRules = rules.filter((r) => r.source === 'custom');

  const formTitle = editing?.mode === 'builtin'
    ? `Customize platform policy: ${editing.name}`
    : editing?.id
      ? 'Edit custom policy'
      : 'New custom policy';

  if (loading && rules.length === 0) {
    return (
      <div className="provision-loading">
        <div className="provision-spinner" />
        <span>Loading policy rules…</span>
      </div>
    );
  }

  return (
    <div className="provision-policies-panel">
      <div className="provision-policies-header">
        <div>
          <h3>Governance policies</h3>
          <p>
            {counts.builtin} platform rules
            {counts.override > 0 ? ` · ${counts.override} customized` : ''}
            {counts.custom > 0 ? ` · ${counts.custom} custom` : ''}
            {' '}
            — evaluated before any new stack is deployed.
          </p>
        </div>
        <button type="button" className="btn-provision primary" onClick={openCreate}>
          + Add custom policy
        </button>
      </div>

      {error && <div className="provision-policy-error">{error}</div>}

      {showForm && (
        <div className="provision-policy-form-card" role="dialog" aria-label="Policy editor">
          <h4>{formTitle}</h4>
          <form onSubmit={handleSave}>
            {editing?.mode !== 'builtin' && (
              <label>
                Name (snake_case)
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="require_project_tag"
                  disabled={!!editing?.id}
                  required
                />
              </label>
            )}
            <label>
              Severity
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
              >
                <option value="warning">Warning (allow deploy)</option>
                <option value="block">Block (prevent deploy)</option>
              </select>
            </label>
            <label>
              Description
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                required
              />
            </label>
            <label>
              Condition
              <textarea
                value={form.condition}
                onChange={(e) => setForm({ ...form, condition: e.target.value })}
                rows={2}
                placeholder="instance_type not in ['t2.micro', 't3.micro']"
                required
              />
            </label>
            <div className="provision-condition-hints">
              <span>Examples:</span>
              {CONDITION_HINTS.map((h) => (
                <button
                  key={h.label}
                  type="button"
                  className="provision-hint-chip"
                  onClick={() => setForm({ ...form, condition: h.value })}
                >
                  {h.label}
                </button>
              ))}
            </div>
            {formError && <p className="provision-form-error">{formError}</p>}
            <div className="provision-policy-form-actions">
              <button type="button" className="btn-provision secondary" onClick={closeForm}>
                Cancel
              </button>
              <button type="submit" className="btn-provision primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </form>
        </div>
      )}

      {customRules.length > 0 && (
        <section className="provision-policy-section">
          <h4 className="provision-policy-section-title">Your custom policies</h4>
          <div className="policy-results">
            {customRules.map((rule) => (
              <div
                key={rule.id || rule.name}
                className={`policy-item ${rule.severity === 'block' ? 'block' : 'warning'} ${!rule.enabled ? 'policy-item--disabled' : ''}`}
              >
                <div className="policy-item-body">
                  <div className="policy-item-name">
                    {rule.severity === 'block' ? 'Block' : 'Warning'} · {rule.name}
                    {!rule.enabled && <span className="policy-source-tag">disabled</span>}
                  </div>
                  <div className="policy-item-desc">{(rule.description || '').trim()}</div>
                  <code className="policy-condition-snippet">{rule.condition}</code>
                </div>
                <div className="policy-item-actions">
                  <span className={`policy-badge ${rule.severity === 'block' ? 'block' : 'warning'}`}>
                    {rule.severity}
                  </span>
                  <button type="button" className="btn-provision secondary small" onClick={() => handleToggleCustom(rule)}>
                    {rule.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button type="button" className="btn-provision secondary small" onClick={() => openEditCustom(rule)}>
                    Edit
                  </button>
                  <button type="button" className="btn-provision secondary small danger" onClick={() => handleDeleteCustom(rule)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="provision-policy-section">
        <h4 className="provision-policy-section-title">Platform policies</h4>
        <div className="policy-results">
          {platformRules.map((rule) => (
            <div
              key={rule.name}
              className={`policy-item ${rule.severity === 'block' ? 'block' : 'warning'} ${!rule.enabled ? 'policy-item--disabled' : ''}`}
            >
              <div className="policy-item-body">
                <div className="policy-item-name">
                  {rule.severity === 'block' ? 'Block' : 'Warning'} · {rule.name}
                  {rule.source === 'override' && rule.enabled && (
                    <span className="policy-source-tag">customized</span>
                  )}
                  {!rule.enabled && <span className="policy-source-tag">disabled</span>}
                </div>
                <div className="policy-item-desc">{(rule.description || '').trim()}</div>
                {(rule.source === 'override' || rule.is_customized) && rule.condition && (
                  <code className="policy-condition-snippet">{rule.condition}</code>
                )}
              </div>
              <div className="policy-item-actions">
                <span className={`policy-badge ${rule.severity === 'block' ? 'block' : 'warning'}`}>
                  {rule.severity}
                </span>
                {rule.enabled ? (
                  <>
                    <button type="button" className="btn-provision secondary small" onClick={() => openCustomizeBuiltin(rule)}>
                      Customize
                    </button>
                    <button type="button" className="btn-provision secondary small" onClick={() => handleDisableBuiltin(rule)}>
                      Disable
                    </button>
                  </>
                ) : (
                  <button type="button" className="btn-provision secondary small" onClick={() => handleEnableBuiltin(rule)}>
                    Enable
                  </button>
                )}
                {rule.can_reset && (
                  <button type="button" className="btn-provision secondary small" onClick={() => handleResetBuiltin(rule)}>
                    Reset
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
