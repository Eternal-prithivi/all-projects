// =============================================================================
// PAGE: ProvisionPage.jsx — Infrastructure governance (Zenith-scoped)
// BYOC: connect AWS once in Settings — no duplicate credential UI here.
// Tabs: Manage deployments | Activity | Policies | New stack (optional Terraform)
// ROUTE: /dashboard/provision
// =============================================================================
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import '../styles/provision.css';
import PageHeader from '../components/ui/PageHeader.jsx';
import ProvisionManagePanel from '../components/provision/ProvisionManagePanel.jsx';
import ProvisionActivityPanel from '../components/provision/ProvisionActivityPanel.jsx';
import ProvisionPoliciesPanel from '../components/provision/ProvisionPoliciesPanel.jsx';
import ProvisionDeployWizard from '../components/provision/ProvisionDeployWizard.jsx';

const TABS = [
  { id: 'manage', label: 'Deployments' },
  { id: 'activity', label: 'Activity' },
  { id: 'policies', label: 'Policies' },
  { id: 'deploy', label: 'New stack' },
];

export default function ProvisionPage() {
  const [tab, setTab] = useState('manage');
  const [awsByocConnected, setAwsByocConnected] = useState(null);
  const [gcpByocConnected, setGcpByocConnected] = useState(false);
  const [azureByocConnected, setAzureByocConnected] = useState(false);
  const [terraformOk, setTerraformOk] = useState(null);
  const [userProvisionEngine, setUserProvisionEngine] = useState('boto3');
  const [hostingHint, setHostingHint] = useState('');
  const [deploymentCount, setDeploymentCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [byocRes, statusRes] = await Promise.all([
          api.get('/byoc/status'),
          api.get('/provision/status').catch(() => ({ data: {} })),
        ]);
        if (cancelled) return;
        setAwsByocConnected(!!byocRes.data?.connections?.aws?.connected);
        setGcpByocConnected(!!byocRes.data?.connections?.gcp?.connected);
        setAzureByocConnected(!!byocRes.data?.connections?.azure?.connected);
        setTerraformOk(statusRes.data?.terraform_installed ?? false);
        setUserProvisionEngine(statusRes.data?.user_provision_engine || 'boto3');
        setHostingHint(statusRes.data?.hosting_hint || '');
      } catch {
        if (!cancelled) setAwsByocConnected(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (awsByocConnected === null) {
    return (
      <div className="provision-page">
        <div className="provision-loading">
          <div className="provision-spinner" />
          <span>Loading…</span>
        </div>
      </div>
    );
  }

  const anyByocConnected = awsByocConnected || gcpByocConnected || azureByocConnected;

  if (!anyByocConnected) {
    return (
      <div className="provision-page">
        <PageHeader
          kicker="Infrastructure"
          title="Infrastructure & optimization"
          subtitle="Connect a cloud account in Settings to deploy stacks and use dashboard features."
        />
        <div className="provision-settings-cta">
          <h3>No cloud account connected</h3>
          <p>
            Connect AWS, GCP, or Azure under <strong>Settings</strong> (BYOC), then return here to
            plan and apply Terraform stacks.
          </p>
          <Link to="/dashboard/settings" className="btn-provision primary">
            Open Settings →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="provision-page">
      <PageHeader
        kicker="Infrastructure"
        title="Infrastructure governance"
        subtitle="Deploy stacks on AWS (Boto3 or Terraform), GCP, or Azure (Terraform). Credentials come from Settings."
      />

      <div className="provision-status-bar">
        <span className="status-dot online" />
        <span>
          {[
            awsByocConnected && 'AWS',
            gcpByocConnected && 'GCP',
            azureByocConnected && 'Azure',
          ]
            .filter(Boolean)
            .join(' · ') || 'Cloud'}{' '}
          connected
        </span>
        <span className="provision-status-sep">·</span>
        <span>
          Engine: <strong>{userProvisionEngine === 'terraform' ? 'Terraform' : 'Boto3'}</strong>
          {userProvisionEngine === 'terraform' && !terraformOk && (
            <span style={{ color: 'var(--warning, #f0ad4e)', marginLeft: '0.35rem' }}>
              (CLI not on server — switch to Boto3 in Settings)
            </span>
          )}
        </span>
        {hostingHint && (
          <>
            <span className="provision-status-sep">·</span>
            <span style={{ opacity: 0.85, fontSize: '0.9em' }}>{hostingHint}</span>
          </>
        )}
      </div>

      <nav className="provision-tabs" aria-label="Infrastructure sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`provision-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.id === 'manage' && deploymentCount > 0 && (
              <span className="provision-tab-badge">{deploymentCount}</span>
            )}
          </button>
        ))}
      </nav>

      {tab === 'manage' && (
        <ProvisionManagePanel onDeploymentsChange={setDeploymentCount} />
      )}
      {tab === 'activity' && <ProvisionActivityPanel />}
      {tab === 'policies' && <ProvisionPoliciesPanel />}
      {tab === 'deploy' && (
        <>
          {userProvisionEngine === 'terraform' && !terraformOk && (
            <div className="provision-empty-state" style={{ marginBottom: '1rem' }}>
              <p>
                Terraform CLI is not available on this server. Use <strong>Boto3</strong> in Settings for
                deployments on Render free tier, or deploy the backend Docker image with Terraform installed.
              </p>
            </div>
          )}
          <ProvisionDeployWizard
            terraformOk={terraformOk}
            userProvisionEngine={userProvisionEngine}
            onDeployed={() => {
              setTab('manage');
              setDeploymentCount((c) => c + 1);
            }}
          />
        </>
      )}
    </div>
  );
}
