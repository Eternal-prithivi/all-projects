// =============================================================================
// PAGE: ProvisionPage.jsx — Infrastructure governance (Zenith-scoped)
// BYOC or platform: available clouds from GET /api/cloud/availability
// Tabs: Manage deployments | Activity | Policies | New stack (optional Terraform)
// ROUTE: /dashboard/provision
// =============================================================================
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import '../styles/provision.css';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import CloudAvailabilityBanner from '../components/CloudAvailabilityBanner.jsx';
import { useCloudAvailability } from '../hooks/useCloudAvailability.js';
import ProvisionManagePanel from '../components/provision/ProvisionManagePanel.jsx';
import ProvisionActivityPanel from '../components/provision/ProvisionActivityPanel.jsx';
import ProvisionPoliciesPanel from '../components/provision/ProvisionPoliciesPanel.jsx';
import ProvisionDeployWizard from '../components/provision/ProvisionDeployWizard.jsx';

const TABS = [
  { id: 'manage', label: 'Deployments' },
  { id: 'activity', label: 'Activity' },
  { id: 'policies', label: 'Policies' },
  { id: 'deploy', label: 'Build' },
];

export default function ProvisionPage() {
  const [tab, setTab] = useState('manage');
  const { loading: availLoading, getFeature, credentialMode } = useCloudAvailability();
  const provisionProviders = getFeature('provision').providers || [];
  const [terraformOk, setTerraformOk] = useState(null);
  const [userProvisionEngine, setUserProvisionEngine] = useState('boto3');
  const [hostingHint, setHostingHint] = useState('');
  const [deploymentCount, setDeploymentCount] = useState(0);
  const [panelReloadToken, setPanelReloadToken] = useState(0);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

  const reloadProvisionStatus = async () => {
    const statusRes = await api.get('/provision/status').catch(() => ({ data: {} }));
    setTerraformOk(statusRes.data?.terraform_installed ?? false);
    setUserProvisionEngine(statusRes.data?.user_provision_engine || 'boto3');
    setHostingHint(statusRes.data?.hosting_hint || '');
    setPanelReloadToken((t) => t + 1);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const statusRes = await api.get('/provision/status').catch(() => ({ data: {} }));
        if (cancelled) return;
        setTerraformOk(statusRes.data?.terraform_installed ?? false);
        setUserProvisionEngine(statusRes.data?.user_provision_engine || 'boto3');
        setHostingHint(statusRes.data?.hosting_hint || '');
      } catch {
        if (!cancelled) setTerraformOk(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (availLoading) {
    return (
      <div className="provision-page">
        <div className="provision-loading">
          <div className="provision-spinner" />
          <span>Loading…</span>
        </div>
      </div>
    );
  }

  if (provisionProviders.length === 0) {
    return (
      <div className="provision-page">
        <PageHeader
          kicker="Infrastructure"
          title="Infrastructure & optimization"
          subtitle="Connect or configure a cloud account to deploy stacks."
        />
        <CloudAvailabilityBanner
          featureLabel="infrastructure provisioning"
          credentialMode={credentialMode}
        />
      </div>
    );
  }

  return (
    <div className="provision-page">
      <PageHeader
        kicker="Infrastructure"
        title="Infrastructure governance"
        subtitle={
          credentialMode === 'byoc'
            ? 'Describe what you need — build the right stack once in your connected cloud accounts.'
            : 'Describe what you need — build on Zenith platform clouds or connect BYOC in Settings.'
        }
        onRefresh={() =>
          runPageRefresh(reloadProvisionStatus, {
            loadingMessage: 'Refreshing provision page…',
            successMessage: 'Provision page refreshed.',
            errorMessage: 'Failed to refresh provision page.',
          })
        }
        refreshing={pageRefreshing}
      />

      <div className="provision-status-bar">
        <span className="status-dot online" />
        <span>
          {provisionProviders.join(' · ')} available
          {credentialMode === 'platform' ? ' (platform)' : ' (BYOC)'}
        </span>
        <span className="provision-status-sep">·</span>
        <span>
          Engine: <strong>{userProvisionEngine === 'terraform' ? 'Terraform' : 'Boto3'}</strong>
          {userProvisionEngine === 'terraform' && !terraformOk && (
            <span style={{ color: 'var(--warning, #f0ad4e)', marginLeft: '0.35rem' }}>
              (CLI not on server — switch to Boto3 in Settings for AWS)
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
        <ProvisionManagePanel
          key={`manage-${panelReloadToken}`}
          onDeploymentsChange={setDeploymentCount}
        />
      )}
      {tab === 'activity' && <ProvisionActivityPanel key={`activity-${panelReloadToken}`} />}
      {tab === 'policies' && <ProvisionPoliciesPanel key={`policies-${panelReloadToken}`} />}
      {tab === 'deploy' && (
        <>
          {userProvisionEngine === 'terraform' && !terraformOk && (
            <div className="provision-empty-state" style={{ marginBottom: '1rem' }}>
              <p>
                Terraform CLI is not available on this server. Use <strong>Boto3</strong> in Settings for
                AWS, or ensure Terraform is installed for GCP/Azure.
              </p>
            </div>
          )}
          <ProvisionDeployWizard
            terraformOk={terraformOk}
            userProvisionEngine={userProvisionEngine}
            availableProviders={provisionProviders}
            defaultProvider={getFeature('provision').default}
            onDeployed={() => setTab('manage')}
          />
        </>
      )}
    </div>
  );
}
