import React from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader.jsx';
import ByocSetupGuidePanel from '../components/byoc/ByocSetupGuidePanel.jsx';
import { BYOC_CAPABILITY_MATRIX, formatFeatureList } from '../data/byocCapabilityMatrix';
import '../styles/settings.css';

export default function ByocSetupHelpPage() {
  return (
    <div className="settings-page byoc-help-page">
      <PageHeader
        kicker="Help"
        title="BYOC optional setup"
        subtitle="Recommended credentials for Cost, VMs, and Provision — storage connect never requires these"
      />

      <div className="settings-content">
        <div className="settings-card">
          <p>
            Zenith uses a <strong>two-tier</strong> BYOC model. Tier 1 (storage keys) unlocks file storage immediately.
            Tier 2 is recommended for additional dashboard areas and can be completed anytime in{' '}
            <Link to="/dashboard/settings">Settings</Link>.
          </p>
          <table className="byoc-help-matrix-table">
            <thead>
              <tr>
                <th>Cloud</th>
                <th>Works after storage-only connect</th>
                <th>Blocked until Tier 2</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(BYOC_CAPABILITY_MATRIX).map(([csp, row]) => (
                <tr key={csp}>
                  <td>{csp}</td>
                  <td>{formatFeatureList(row.worksAfterStorageOnly)}</td>
                  <td>{row.blockedUntilTier2.length ? formatFeatureList(row.blockedUntilTier2) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="settings-card">
          <h3>Google Cloud — billing export</h3>
          <ByocSetupGuidePanel tier="gcp_billing" defaultOpen />
        </div>

        <div className="settings-card">
          <h3>Microsoft Azure — service principal</h3>
          <ByocSetupGuidePanel tier="azure_compute" defaultOpen />
        </div>

        <p>
          <Link to="/dashboard/settings" className="btn-secondary">Back to Settings</Link>
        </p>
      </div>
    </div>
  );
}
