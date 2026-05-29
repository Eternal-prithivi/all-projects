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
  const [userPermissions, setUserPermissions] = useState(null);
  const [terraformOk, setTerraformOk] = useState(null);
  const [deploymentCount, setDeploymentCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [byocRes, permRes, statusRes] = await Promise.all([
          api.get('/byoc/status'),
          api.get('/provision/my-permissions').catch(() => ({ data: null })),
          api.get('/provision/status').catch(() => ({ data: {} })),
        ]);
        if (cancelled) return;
        setAwsByocConnected(!!byocRes.data?.aws?.connected);
        if (permRes.data) setUserPermissions(permRes.data);
        setTerraformOk(statusRes.data?.terraform_installed ?? false);
        if (statusRes.data?.user_permissions) setUserPermissions(statusRes.data.user_permissions);
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

  if (!awsByocConnected) {
    return (
      <div className="provision-page">
        <PageHeader
          kicker="Infrastructure"
          title="Infrastructure & optimization"
          subtitle="Connect your AWS account once in Settings — Zenith uses it for cost, storage, and VM optimization. No separate setup needed here."
        />
        <div className="provision-settings-cta">
          <h3>AWS not connected</h3>
          <p>
            Bring your own cloud credentials in <strong>Settings</strong> to unlock cost analysis,
            storage tiering, VM cluster, and security features across the dashboard.
          </p>
          <Link to="/dashboard/settings" className="btn-provision primary">
            Connect AWS in Settings →
          </Link>
          <p className="provision-empty-hint" style={{ marginTop: '1.5rem' }}>
            Optional Terraform stacks (new VPC, EC2, S3, etc.) are available after AWS is connected,
            under the <strong>New stack</strong> tab on this page.
          </p>
        </div>
      </div>
    );
  }

  const visibleTabs = TABS.filter((t) => {
    if (t.id === 'deploy' && userPermissions && !userPermissions.can_plan) return false;
    return true;
  });

  return (
    <div className="provision-page">
      <PageHeader
        kicker="Infrastructure"
        title="Infrastructure governance"
        subtitle="Manage Terraform deployments, drift, and policies. AWS credentials come from Settings — not configured again here."
      />

      <div className="provision-status-bar">
        <span className="status-dot online" />
        <span>AWS connected via Settings</span>
        {userPermissions && (
          <span className="role-badge" style={{ marginLeft: 'auto' }}>
            Role: {userPermissions.provision_role}
            {userPermissions.can_apply ? ' · can deploy' : ' · view / plan'}
          </span>
        )}
      </div>

      <nav className="provision-tabs" aria-label="Infrastructure sections">
        {visibleTabs.map((t) => (
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
        <ProvisionManagePanel
          userPermissions={userPermissions}
          onDeploymentsChange={setDeploymentCount}
        />
      )}
      {tab === 'activity' && <ProvisionActivityPanel />}
      {tab === 'policies' && <ProvisionPoliciesPanel />}
      {tab === 'deploy' && (
        <>
          {!terraformOk && (
            <div className="provision-empty-state" style={{ marginBottom: '1rem' }}>
              <p>Terraform CLI is not available on the server. Contact your administrator to enable deployments.</p>
            </div>
          )}
          <ProvisionDeployWizard
            userPermissions={userPermissions}
            terraformOk={terraformOk}
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
