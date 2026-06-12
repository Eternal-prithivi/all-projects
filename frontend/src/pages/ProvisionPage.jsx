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
import CloudCapabilityBanner from '../components/cloud/CloudCapabilityBanner.jsx';
import CredentialSourceBadge from '../components/cloud/CredentialSourceBadge.jsx';
import { useCloudAvailability } from '../hooks/useCloudAvailability.js';
import ProvisionManagePanel from '../components/provision/ProvisionManagePanel.jsx';
import ProvisionActivityPanel from '../components/provision/ProvisionActivityPanel.jsx';
import ProvisionPoliciesPanel from '../components/provision/ProvisionPoliciesPanel.jsx';
import ProvisionDeployWizard from '../components/provision/ProvisionDeployWizard.jsx';
import { getEffectiveEngineLabel } from '../utils/provisionEngine.js';
import { usePlanEntitlementsContext } from '../context/PlanEntitlementsContext.jsx';
import PlanUpgradeGate from '../components/billing/PlanUpgradeGate.jsx';
import { NAV_ID_LABELS, MIN_PLAN_LABELS } from '../config/planNavConfig.js';

const TABS = [
  { id: 'manage', label: 'Deployments' },
  { id: 'activity', label: 'Activity' },
  { id: 'policies', label: 'Policies' },
  { id: 'deploy', label: 'Build' },
];

export default function ProvisionPage() {
  const {
    isFeatureEnabled,
    isNavLocked,
    openUpgradeDrawer,
    planName,
    getNavMeta,
  } = usePlanEntitlementsContext();
  const [tab, setTab] = useState('manage');
  const {
    loading: availLoading,
    data: availData,
    getFeature,
    credentialMode,
    getLockedProviders,
    getCredentialSource,
  } = useCloudAvailability();
  const provisionProviders = getFeature('provision').providers || [];
  const [terraformOk, setTerraformOk] = useState(null);
  const [userProvisionEngine, setUserProvisionEngine] = useState('boto3');
  const [hostingHint, setHostingHint] = useState('');
  const [deploymentCount, setDeploymentCount] = useState(0);
  const [panelReloadToken, setPanelReloadToken] = useState(0);
  const [engineSaving, setEngineSaving] = useState(false);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const defaultCloud = getFeature('provision').default || provisionProviders[0] || 'AWS';

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

  const handleEngineChange = async (nextEngine) => {
    if (nextEngine === userProvisionEngine || engineSaving) return;
    setEngineSaving(true);
    try {
      const { data } = await api.get('/settings/');
      const prefs = data?.preferences || {};
      await api.put('/settings/preferences', {
        theme: prefs.theme || 'dark',
        language: prefs.language || 'en',
        timezone: prefs.timezone || 'UTC-5',
        date_format: prefs.date_format || 'MM/DD/YYYY',
        currency: prefs.currency || 'USD',
        provision_engine: nextEngine,
        platform_region_slug: prefs.platform_region_slug || null,
        default_lifecycle_policy: prefs.default_lifecycle_policy || 'auto',
        lifecycle_notice_days: prefs.lifecycle_notice_days ?? 7,
        default_security_encryption: prefs.default_security_encryption || 'ask',
        always_ask_encryption: Boolean(prefs.always_ask_encryption),
        default_security_csp: prefs.default_security_csp || 'AWS',
        default_security_replication: Boolean(prefs.default_security_replication),
        stale_file_days: prefs.stale_file_days ?? 90,
        stale_notice_days: prefs.stale_notice_days ?? 7,
        ml_assisted_scan: prefs.ml_assisted_scan !== false,
      });
      setUserProvisionEngine(nextEngine);
    } catch {
      /* keep current selection */
    } finally {
      setEngineSaving(false);
    }
  };

  if (availLoading && !availData) {
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

      <CloudCapabilityBanner
        feature="provision"
        lockedProviders={getLockedProviders('provision')}
        className="provision-capability-banner"
      />

      <div className="provision-status-bar">
        <div className="provision-status-bar__row">
          <span className="status-dot online" />
          <span>
            {provisionProviders.join(' · ')} available
            {defaultCloud && (
              <CredentialSourceBadge
                source={getCredentialSource(defaultCloud, 'provision')}
                className="provision-credential-badge"
              />
            )}
            {credentialMode === 'hybrid'
              ? ' (BYOC + platform)'
              : credentialMode === 'platform'
                ? ' (platform)'
                : ' (BYOC)'}
          </span>
        </div>
        <div className="provision-status-bar__row provision-status-bar__engine">
          <span className="provision-status-bar__engine-label">Provision with</span>
          <div className="provision-engine-toggle" role="group" aria-label="Provisioning engine">
            <button
              type="button"
              className={`provision-engine-toggle__btn ${userProvisionEngine !== 'terraform' ? 'active' : ''}`}
              disabled={engineSaving}
              onClick={() => handleEngineChange('boto3')}
            >
              Fast path
              <span className="provision-engine-toggle__hint">
                {getEffectiveEngineLabel('boto3')}
              </span>
            </button>
            <button
              type="button"
              className={`provision-engine-toggle__btn ${userProvisionEngine === 'terraform' ? 'active' : ''}`}
              disabled={engineSaving || !terraformOk}
              onClick={() => handleEngineChange('terraform')}
              title={!terraformOk ? 'Terraform CLI is not installed on this server' : undefined}
            >
              Terraform
              {!terraformOk && (
                <span className="provision-engine-toggle__warn"> (unavailable)</span>
              )}
            </button>
          </div>
          <span className="provision-status-bar__engine-note">
            Fast path uses each cloud&apos;s native SDK (AWS, GCP, Azure). Terraform provisions all modules when installed.
          </span>
        </div>
        {hostingHint && (
          <p className="provision-status-bar__hint">{hostingHint}</p>
        )}
      </div>

      <nav className="provision-tabs" aria-label="Infrastructure sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`provision-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => {
              if (t.id === 'policies' && isNavLocked('provision_policies')) {
                openUpgradeDrawer('provision_policies');
                return;
              }
              setTab(t.id);
            }}
          >
            {t.label}
            {t.id === 'policies' && isNavLocked('provision_policies') && (
              <span className="provision-tab-lock" aria-hidden>🔒</span>
            )}
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
      {tab === 'policies' && (
        isFeatureEnabled('provision_policies') ? (
          <ProvisionPoliciesPanel key={`policies-${panelReloadToken}`} />
        ) : (
          <PlanUpgradeGate
            featureLabel={NAV_ID_LABELS.provision_policies}
            currentPlan={planName}
            requiredPlan={MIN_PLAN_LABELS[getNavMeta('provision_policies')?.min_plan] || 'Pro'}
            requiredPlanId={getNavMeta('provision_policies')?.min_plan || 'pro'}
          />
        )
      )}
      {tab === 'deploy' && (
        <>
          {userProvisionEngine === 'terraform' && !terraformOk && (
            <div className="provision-empty-state" style={{ marginBottom: '1rem' }}>
              <p>
                Terraform CLI is not available on this server. Use <strong>Fast path</strong> above
                (Cloud SDK) or install Terraform for full module coverage.
              </p>
            </div>
          )}
          <ProvisionDeployWizard
            terraformOk={terraformOk}
            userProvisionEngine={userProvisionEngine}
            availableProviders={provisionProviders}
            defaultProvider={defaultCloud}
            onDeployed={() => setTab('manage')}
            onEngineChange={handleEngineChange}
          />
        </>
      )}
    </div>
  );
}
