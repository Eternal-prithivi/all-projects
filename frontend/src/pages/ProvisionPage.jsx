// =============================================================================
// PAGE: ProvisionPage.jsx
// PURPOSE: AWS Infrastructure Provisioning Wizard — 4-step wizard + deployments
//   Step 1: Choose template or custom modules
//   Step 2: Configure module parameters
//   Step 3: Policy check + cost estimate review
//   Step 4: Terraform plan/apply output
// ROUTE: /dashboard/provision
// API: /api/provision/* endpoints
// DO NOT:
//   - Allow apply without policy check passing
//   - Remove cost estimation — users need to know charges before deploying
//   - Skip the plan step — always preview before applying
// =============================================================================
import React, { useState, useEffect, useCallback, useRef } from 'react';
import api from '../api';
import '../styles/provision.css';
import PageHeader from '../components/ui/PageHeader.jsx';

// ── Templates & Modules data (also returned by API, but hardcoded for instant render) ──

const TEMPLATES = [
  {
    key: 'static-site',
    name: 'Static Website',
    description: 'Host a static HTML/CSS/JS website on S3. Private, encrypted, free tier eligible.',
    icon: '🌐',
    cost: '$0.00/month',
    services: { enable_s3: true },
  },
  {
    key: 'backend-app',
    name: 'Backend Application',
    description: 'EC2 instance with VPC networking, IAM role, and CloudWatch monitoring.',
    icon: '🖥️',
    cost: '$0.00/month',
    services: { enable_vpc: true, enable_ec2: true, enable_iam: true, enable_cloudwatch: true },
  },
  {
    key: 'serverless-db',
    name: 'Serverless Database',
    description: 'DynamoDB table with provisioned capacity within AWS always-free limits.',
    icon: '🗄️',
    cost: '$0.00/month',
    services: { enable_dynamodb: true },
  },
];

const MODULES = [
  { key: 'vpc', name: 'VPC', desc: 'Virtual Private Cloud with public/private subnets', flag: 'enable_vpc' },
  { key: 'ec2', name: 'EC2', desc: 'Elastic Compute Cloud instance', flag: 'enable_ec2', requires: ['vpc'] },
  { key: 's3', name: 'S3', desc: 'Simple Storage Service bucket', flag: 'enable_s3' },
  { key: 'iam', name: 'IAM', desc: 'Identity & Access Management role', flag: 'enable_iam' },
  { key: 'cloudwatch', name: 'CloudWatch', desc: 'Monitoring & alerting', flag: 'enable_cloudwatch', requires: ['ec2'] },
  { key: 'dynamodb', name: 'DynamoDB', desc: 'NoSQL database table', flag: 'enable_dynamodb' },
];

const STEP_LABELS = ['Choose', 'Configure', 'Review', 'Deploy'];

export default function ProvisionPage() {
  // ── State ──
  const [step, setStep] = useState(0);
  const [terraformOk, setTerraformOk] = useState(null); // null = loading, true/false
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [userPermissions, setUserPermissions] = useState(null);

  const [config, setConfig] = useState({
    template: null,
    aws_region: 'ap-south-1',
    enable_vpc: false,
    enable_ec2: false,
    enable_s3: false,
    enable_iam: false,
    enable_cloudwatch: false,
    enable_dynamodb: false,
    vpc_cidr: '10.0.0.0/16',
    instance_type: 't2.micro',
    instance_name: '',
    ami_id: '',
    bucket_name: '',
    role_name: 'app-role',
    alarm_email: '',
    budget_limit: '1',
    budget_email: '',
    dynamodb_table_name: '',
    dynamodb_hash_key: 'id',
    dynamodb_read_capacity: 5,
    dynamodb_write_capacity: 5,
    tags: { Env: 'free-tier' },
    environment: 'free-tier',
  });

  const [policyResult, setPolicyResult] = useState(null);
  const [costEstimate, setCostEstimate] = useState(null);
  const [planOutput, setPlanOutput] = useState('');
  const [deploymentId, setDeploymentId] = useState(null);
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const terminalRef = useRef(null);

  // ── Startup: check Terraform + load deployments ──
  useEffect(() => {
    checkTerraformStatus();
    loadDeployments();
    loadPermissions();
  }, []);

  const checkTerraformStatus = async () => {
    try {
      const res = await api.get('/provision/status');
      setTerraformOk(res.data.terraform_installed);
      if (res.data.user_permissions) {
        setUserPermissions(res.data.user_permissions);
      }
    } catch {
      setTerraformOk(false);
    }
  };

  const loadPermissions = async () => {
    try {
      const res = await api.get('/provision/my-permissions');
      setUserPermissions(res.data);
    } catch {
      // Silent — permissions badge just won't show
    }
  };

  const loadDeployments = async () => {
    try {
      const res = await api.get('/provision/deployments');
      setDeployments(res.data.deployments || []);
    } catch {
      // Silent — deployments section just won't show
    }
  };

  // ── Step 1: Template Selection ──
  const selectTemplate = (tmpl) => {
    if (selectedTemplate === tmpl.key) {
      // Deselect
      setSelectedTemplate(null);
      setConfig(prev => ({
        ...prev,
        template: null,
        enable_vpc: false, enable_ec2: false, enable_s3: false,
        enable_iam: false, enable_cloudwatch: false, enable_dynamodb: false,
      }));
    } else {
      setSelectedTemplate(tmpl.key);
      setConfig(prev => ({
        ...prev,
        template: tmpl.key,
        enable_vpc: !!tmpl.services.enable_vpc,
        enable_ec2: !!tmpl.services.enable_ec2,
        enable_s3: !!tmpl.services.enable_s3,
        enable_iam: !!tmpl.services.enable_iam,
        enable_cloudwatch: !!tmpl.services.enable_cloudwatch,
        enable_dynamodb: !!tmpl.services.enable_dynamodb,
      }));
    }
  };

  const toggleModule = (flag) => {
    setSelectedTemplate(null); // Custom mode
    setConfig(prev => {
      const next = { ...prev, template: 'custom', [flag]: !prev[flag] };
      // Auto-enable VPC when EC2 is enabled
      if (flag === 'enable_ec2' && next.enable_ec2) next.enable_vpc = true;
      // Auto-enable EC2 when CloudWatch is enabled
      if (flag === 'enable_cloudwatch' && next.enable_cloudwatch) {
        next.enable_ec2 = true;
        next.enable_vpc = true;
      }
      return next;
    });
  };

  const hasAnyModule = config.enable_vpc || config.enable_ec2 || config.enable_s3 ||
    config.enable_iam || config.enable_cloudwatch || config.enable_dynamodb;

  // ── Step 2: Config field update ──
  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  // ── Step 3: Run policy check + cost estimate ──
  const runReview = async () => {
    setLoading(true);
    setError(null);
    try {
      const [policyRes, costRes] = await Promise.all([
        api.post('/provision/policy-check', config),
        api.post('/provision/estimate', config),
      ]);
      setPolicyResult(policyRes.data);
      setCostEstimate(costRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to run review');
    } finally {
      setLoading(false);
    }
  };

  // ── Step 4: Run plan ──
  const runPlan = async () => {
    setLoading(true);
    setError(null);
    setPlanOutput('');
    try {
      const res = await api.post('/provision/plan', config);
      setPlanOutput(res.data.plan_output || '');
      setDeploymentId(res.data.deployment_id);
      setPolicyResult(res.data.policy_check);
      setCostEstimate(res.data.cost_estimate);
      if (!res.data.success) {
        setError(res.data.error || 'Terraform plan failed');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to run terraform plan');
    } finally {
      setLoading(false);
    }
  };

  // ── Apply ──
  const runApply = async () => {
    if (!deploymentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/provision/apply/${deploymentId}`);
      if (res.data.success) {
        setPlanOutput(prev => prev + '\n\n✅ Apply complete! ' + res.data.resources_count + ' resources created.');
        loadDeployments();
      } else {
        setError(res.data.error || 'Terraform apply failed');
        setPlanOutput(prev => prev + '\n\n❌ Apply failed: ' + (res.data.error || 'unknown error'));
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to apply');
    } finally {
      setLoading(false);
    }
  };

  // ── Destroy ──
  const runDestroy = async (depId) => {
    if (!window.confirm('Are you sure you want to destroy this deployment? This cannot be undone.')) return;
    setLoading(true);
    try {
      await api.post(`/provision/destroy/${depId}`);
      loadDeployments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Destroy failed');
    } finally {
      setLoading(false);
    }
  };

  // ── Drift Check ──
  const runDriftCheck = async (depId) => {
    setLoading(true);
    try {
      await api.post(`/provision/deployments/${depId}/drift`);
      loadDeployments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Drift check failed');
    } finally {
      setLoading(false);
    }
  };

  // ── Drift Remediation ──
  const runRemediate = async (depId, checkOnly = true) => {
    if (!checkOnly && !window.confirm('This will run terraform apply to restore desired state. Continue?')) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/provision/deployments/${depId}/remediate`, { check_only: checkOnly });
      if (res.data.success) {
        setError(null);
        if (res.data.performed) {
          loadDeployments();
        }
        setPlanOutput(res.data.plan_output || res.data.message);
      } else {
        setError(res.data.message || 'Remediation failed');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Remediation failed');
    } finally {
      setLoading(false);
    }
  };

  // ── Step navigation ──
  const nextStep = () => {
    if (step === 2) {
      runReview();
    }
    if (step === 3) {
      runPlan();
    }
    setStep(s => Math.min(s + 1, 3));
  };
  const prevStep = () => setStep(s => Math.max(s - 1, 0));

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [planOutput]);

  // ── Render helpers ──
  const canProceedStep0 = hasAnyModule;
  const canProceedStep1 = true; // Config form is optional
  const canProceedStep2 = policyResult && (!policyResult.blocks || policyResult.blocks.length === 0);

  const getStatusClass = (status) => {
    if (['deployed'].includes(status)) return 'deployed';
    if (['planning', 'applying', 'awaiting_apply'].includes(status)) return 'planning';
    if (['destroyed'].includes(status)) return 'destroyed';
    return 'failed';
  };

  // ════════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════════
  return (
    <div className="provision-page">
      <PageHeader
        kicker="Infrastructure"
        title="Infrastructure Provisioning"
        subtitle="Deploy AWS resources using Terraform — governed by policy, estimated for cost."
      />

      {/* Status Bar */}
      <div className="provision-status-bar">
        <span className={`status-dot ${terraformOk ? 'online' : 'offline'}`} />
        <span>Terraform: {terraformOk === null ? 'checking...' : terraformOk ? '✅ Installed' : '❌ Not found'}</span>
        {userPermissions && (
          <span className="role-badge" style={{ marginLeft: 'auto' }}>
            🔐 Role: {userPermissions.provision_role}
            {userPermissions.can_apply ? ' • Can deploy' : ' • View/plan only'}
          </span>
        )}
      </div>

      {/* Wizard Steps */}
      <div className="wizard-steps">
        {STEP_LABELS.map((label, i) => (
          <React.Fragment key={label}>
            <div
              className={`wizard-step ${i === step ? 'active' : i < step ? 'completed' : 'inactive'}`}
              onClick={() => i < step && setStep(i)}
            >
              <div className="wizard-step-number">
                {i < step ? '✓' : i + 1}
              </div>
              <span className="wizard-step-label">{label}</span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div className={`wizard-step-connector ${i < step ? 'completed' : ''}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="policy-item block" style={{ marginBottom: '1.5rem' }}>
          <div>
            <div className="policy-item-name">⚠️ Error</div>
            <div className="policy-item-desc">{error}</div>
          </div>
        </div>
      )}

      {/* ════════ Step 0: Choose ════════ */}
      {step === 0 && (
        <div>
          <div className="section-header">
            <h3>Quick Start Templates</h3>
            <p>Select a pre-configured template or customize individual modules below.</p>
          </div>

          <div className="template-grid">
            {TEMPLATES.map(tmpl => (
              <div
                key={tmpl.key}
                className={`template-card ${selectedTemplate === tmpl.key ? 'selected' : ''}`}
                onClick={() => selectTemplate(tmpl)}
                id={`template-${tmpl.key}`}
              >
                <div className="template-card-icon">{tmpl.icon}</div>
                <h3>{tmpl.name}</h3>
                <p>{tmpl.description}</p>
                <span className="cost-badge">{tmpl.cost}</span>
              </div>
            ))}
          </div>

          <div className="or-divider">or customize</div>

          <div className="section-header">
            <h3>Individual Modules</h3>
            <p>Toggle specific AWS services. Dependencies are auto-resolved.</p>
          </div>

          <div className="module-toggles">
            {MODULES.map(mod => (
              <div
                key={mod.key}
                className={`module-toggle ${config[mod.flag] ? 'enabled' : ''}`}
                onClick={() => toggleModule(mod.flag)}
                id={`module-${mod.key}`}
              >
                <div className="module-toggle-switch" />
                <div className="module-toggle-info">
                  <h4>{mod.name}</h4>
                  <p>{mod.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="provision-actions">
            <button
              className="btn-provision primary"
              disabled={!canProceedStep0}
              onClick={nextStep}
            >
              Next: Configure →
            </button>
          </div>
        </div>
      )}

      {/* ════════ Step 1: Configure ════════ */}
      {step === 1 && (
        <div>
          <div className="section-header">
            <h3>Configure Resources</h3>
            <p>Set parameters for your selected modules. Defaults are free-tier safe.</p>
          </div>

          <div className="config-form">
            <div className="config-field">
              <label>AWS Region</label>
              <select className="zenith-select" value={config.aws_region} onChange={e => updateConfig('aws_region', e.target.value)}>
                <option value="ap-south-1">Asia Pacific (Mumbai)</option>
                <option value="us-east-1">US East (N. Virginia)</option>
                <option value="us-west-2">US West (Oregon)</option>
                <option value="eu-west-1">Europe (Ireland)</option>
                <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
              </select>
            </div>

            {config.enable_ec2 && (
              <>
                <div className="config-field">
                  <label>Instance Type</label>
                  <select className="zenith-select" value={config.instance_type} onChange={e => updateConfig('instance_type', e.target.value)}>
                    <option value="t2.micro">t2.micro (Free Tier)</option>
                    <option value="t3.micro">t3.micro (Free Tier)</option>
                    <option value="t2.small">t2.small ($16.79/mo)</option>
                    <option value="t2.medium">t2.medium ($33.58/mo)</option>
                    <option value="t3.small">t3.small ($15.18/mo)</option>
                    <option value="t3.medium">t3.medium ($30.37/mo)</option>
                  </select>
                </div>
                <div className="config-field">
                  <label>Instance Name</label>
                  <input
                    type="text"
                    value={config.instance_name}
                    onChange={e => updateConfig('instance_name', e.target.value)}
                    placeholder="zenith-app-server"
                  />
                </div>
              </>
            )}

            {config.enable_s3 && (
              <div className="config-field">
                <label>S3 Bucket Name (globally unique)</label>
                <input
                  type="text"
                  value={config.bucket_name}
                  onChange={e => updateConfig('bucket_name', e.target.value)}
                  placeholder="zenith-my-bucket-2026"
                />
              </div>
            )}

            {config.enable_iam && (
              <div className="config-field">
                <label>IAM Role Name</label>
                <input
                  type="text"
                  value={config.role_name}
                  onChange={e => updateConfig('role_name', e.target.value)}
                  placeholder="zenith-app-role"
                />
              </div>
            )}

            {config.enable_dynamodb && (
              <>
                <div className="config-field">
                  <label>DynamoDB Table Name</label>
                  <input
                    type="text"
                    value={config.dynamodb_table_name}
                    onChange={e => updateConfig('dynamodb_table_name', e.target.value)}
                    placeholder="zenith-data"
                  />
                </div>
                <div className="config-field">
                  <label>Hash Key Name</label>
                  <input
                    type="text"
                    value={config.dynamodb_hash_key}
                    onChange={e => updateConfig('dynamodb_hash_key', e.target.value)}
                    placeholder="id"
                  />
                </div>
              </>
            )}

            {config.enable_cloudwatch && (
              <div className="config-field">
                <label>Alarm Email</label>
                <input
                  type="email"
                  value={config.alarm_email}
                  onChange={e => updateConfig('alarm_email', e.target.value)}
                  placeholder="alerts@example.com"
                />
              </div>
            )}

            <div className="config-field">
              <label>Budget Limit (USD/month)</label>
              <input
                type="text"
                value={config.budget_limit}
                onChange={e => updateConfig('budget_limit', e.target.value)}
                placeholder="1"
              />
            </div>

            <div className="config-field">
              <label>Budget Alert Email</label>
              <input
                type="email"
                value={config.budget_email}
                onChange={e => updateConfig('budget_email', e.target.value)}
                placeholder="billing@example.com"
              />
            </div>
          </div>

          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={prevStep}>← Back</button>
            <button className="btn-provision primary" onClick={nextStep}>
              Next: Review →
            </button>
          </div>
        </div>
      )}

      {/* ════════ Step 2: Review ════════ */}
      {step === 2 && (
        <div>
          <div className="section-header">
            <h3>Policy Check & Cost Estimate</h3>
            <p>Review security policies and estimated costs before deploying.</p>
          </div>

          {loading && (
            <div className="provision-loading">
              <div className="provision-spinner" />
              <span>Running policy check & cost estimate...</span>
            </div>
          )}

          {/* Policy Results */}
          {policyResult && (
            <div className="policy-results">
              <h3>🛡️ Policy Check</h3>

              {policyResult.blocks && policyResult.blocks.length > 0 && (
                <div>
                  <span className="policy-badge block">🚫 {policyResult.blocks.length} Blocked</span>
                  {policyResult.blocks.map((b, i) => (
                    <div key={i} className="policy-item block">
                      <div>
                        <div className="policy-item-name">{b.rule_name}</div>
                        <div className="policy-item-desc">{b.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {policyResult.warnings && policyResult.warnings.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <span className="policy-badge warning">⚠️ {policyResult.warnings.length} Warnings</span>
                  {policyResult.warnings.map((w, i) => (
                    <div key={i} className="policy-item warning">
                      <div>
                        <div className="policy-item-name">{w.rule_name}</div>
                        <div className="policy-item-desc">{w.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {policyResult.can_deploy && (
                <span className="policy-badge passed">✅ All security checks passed</span>
              )}
            </div>
          )}

          {/* Cost Estimate */}
          {costEstimate && costEstimate.resources && costEstimate.resources.length > 0 && (
            <div>
              <h3 style={{ color: 'var(--text-primary, #fff)', marginBottom: '1rem', fontSize: '1.1rem' }}>
                💰 Cost Estimate
              </h3>
              <table className="cost-table">
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Monthly Cost</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {costEstimate.resources.map((r, i) => (
                    <tr key={i}>
                      <td>{r.name}</td>
                      <td>${r.monthly_cost}</td>
                      <td className="cost-note">{r.note || ''}</td>
                    </tr>
                  ))}
                  <tr>
                    <td><strong>Total</strong></td>
                    <td className="cost-total">${costEstimate.total_monthly_cost}/month</td>
                    <td className="cost-note">{costEstimate.currency}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={prevStep}>← Back</button>
            <button
              className="btn-provision primary"
              disabled={!policyResult || !policyResult.can_deploy || loading}
              onClick={nextStep}
            >
              {policyResult && !policyResult.can_deploy
                ? '🚫 Fix policy violations first'
                : 'Next: Run Plan →'}
            </button>
          </div>
        </div>
      )}

      {/* ════════ Step 3: Deploy ════════ */}
      {step === 3 && (
        <div>
          <div className="section-header">
            <h3>Terraform Plan & Apply</h3>
            <p>Review the execution plan, then apply to create real AWS resources.</p>
          </div>

          {loading && !planOutput && (
            <div className="provision-loading">
              <div className="provision-spinner" />
              <span>Running terraform plan...</span>
            </div>
          )}

          {planOutput && (
            <div className="terraform-terminal" ref={terminalRef}>
              {planOutput.split('\n').map((line, i) => {
                let cls = 'tf-line';
                if (line.trim().startsWith('+')) cls += ' tf-add';
                else if (line.trim().startsWith('-')) cls += ' tf-remove';
                else if (line.trim().startsWith('~')) cls += ' tf-change';
                return <div key={i} className={cls}>{line || ' '}</div>;
              })}
            </div>
          )}

          <div className="provision-actions">
            <button className="btn-provision secondary" onClick={() => setStep(0)}>
              ← Start Over
            </button>
            {deploymentId && (
              <button
                className="btn-provision primary"
                disabled={loading}
                onClick={runApply}
              >
                {loading ? (
                  <><div className="provision-spinner" style={{ width: 16, height: 16 }} /> Applying...</>
                ) : (
                  '🚀 Apply — Create Resources'
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* ════════ Active Deployments ════════ */}
      {deployments.length > 0 && (
        <div className="deployments-section">
          <h2>Active Deployments</h2>
          {deployments.map(dep => (
            <div key={dep._id} className="deployment-card">
              <div className="deployment-info">
                <h4>{dep.deployment_name}</h4>
                <div className="deployment-meta">
                  <span className={`deployment-status ${getStatusClass(dep.status)}`}>
                    {dep.status}
                  </span>
                  {dep.enabled_modules && (
                    <span>{dep.enabled_modules.join(', ')}</span>
                  )}
                  <span>{dep.resources_count || 0} resources</span>
                  {dep.latest_drift && dep.latest_drift !== 'unknown' && (
                    <span className={`drift-indicator ${dep.latest_drift === 'clean' ? 'clean' : 'drift'}`}>
                      {dep.latest_drift === 'clean' ? '✓ No drift' : '⚠ Drift detected'}
                    </span>
                  )}
                </div>
              </div>
              <div className="provision-actions" style={{ margin: 0 }}>
                {dep.status === 'deployed' && (
                  <>
                    <button
                      className="btn-provision secondary"
                      onClick={() => runDriftCheck(dep.deployment_name)}
                      disabled={loading}
                    >
                      Check Drift
                    </button>
                    {dep.latest_drift === 'drift_detected' && (
                      <button
                        className="btn-provision primary"
                        onClick={() => runRemediate(dep.deployment_name, false)}
                        disabled={loading || (userPermissions && !userPermissions.can_remediate)}
                        title={userPermissions && !userPermissions.can_remediate ? 'Requires devops or admin role' : 'Apply terraform to fix drift'}
                      >
                        🔧 Fix Drift
                      </button>
                    )}
                    <button
                      className="btn-provision danger"
                      onClick={() => runDestroy(dep.deployment_name)}
                      disabled={loading || (userPermissions && !userPermissions.can_destroy)}
                      title={userPermissions && !userPermissions.can_destroy ? 'Requires devops or admin role' : 'Destroy deployment'}
                    >
                      Destroy
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
