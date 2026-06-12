/** Canonical BYOC Tier 2 setup copy — wizard, help page, and API mirror. */

export const BYOC_SETUP_GUIDES = {
  gcp_billing: {
    id: 'gcp_billing',
    csp: 'GCP',
    title: 'GCP BigQuery billing export (recommended)',
    worksWithout: ['Storage', 'Security', 'VMs', 'Provision'],
    blockedWithout: ['Cost analysis in Zenith'],
    fieldChecklist: [
      { key: 'gcp_billing_dataset_id', label: 'Billing dataset ID', example: 'billing_export' },
      { key: 'gcp_billing_table_id', label: 'Billing table ID', example: 'gcp_billing_export_v1_01ABCD-123456-ABCDEF' },
    ],
    steps: [
      {
        title: 'Enable billing export',
        body: 'In Google Cloud Console, open Billing → Billing export → BigQuery export and enable export to a dataset.',
        link: 'https://console.cloud.google.com/billing/export',
        linkLabel: 'Open Billing export',
      },
      {
        title: 'Note dataset and table IDs',
        body: 'After export runs, open BigQuery and copy the dataset ID (e.g. billing_export) and table name (often gcp_billing_export_v1_<BILLING_ACCOUNT_ID>).',
        link: 'https://console.cloud.google.com/bigquery',
        linkLabel: 'Open BigQuery',
      },
      {
        title: 'Grant the service account access',
        body: 'On the billing export dataset, grant your BYOC service account the BigQuery Data Viewer role (minimum) so Zenith can read cost rows.',
      },
      {
        title: 'Paste IDs in Zenith',
        body: 'Enter both dataset ID and table ID below. You can skip this step and add them later in Settings — Storage will still work.',
      },
    ],
  },
  azure_compute: {
    id: 'azure_compute',
    csp: 'Azure',
    title: 'Azure service principal (recommended)',
    worksWithout: ['Storage', 'Security'],
    blockedWithout: ['VMs', 'Provision', 'Cost analysis'],
    fieldChecklist: [
      { key: 'azure_subscription_id', label: 'Subscription ID', example: '00000000-0000-0000-0000-000000000000' },
      { key: 'azure_tenant_id', label: 'Tenant ID', example: 'Directory (tenant) ID from Azure AD' },
      { key: 'azure_client_id', label: 'Application (client) ID', example: 'App registration client ID' },
      { key: 'azure_client_secret', label: 'Client secret', example: 'From Certificates & secrets' },
    ],
    steps: [
      {
        title: 'Create an app registration',
        body: 'In Azure Portal → Microsoft Entra ID → App registrations → New registration. Name it (e.g. zenith-byoc) and create a client secret under Certificates & secrets.',
        link: 'https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps',
        linkLabel: 'App registrations',
      },
      {
        title: 'Collect subscription and tenant IDs',
        body: 'Subscription ID: Subscriptions blade. Tenant ID: Overview on your Entra ID tenant.',
        link: 'https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBlade',
        linkLabel: 'Subscriptions',
      },
      {
        title: 'Assign roles on the subscription',
        body: 'Grant the app Cost Management Reader (for Cost) and Contributor or a custom role with compute permissions (for VMs and Provision). Role requirements depend on your governance policy.',
      },
      {
        title: 'Paste credentials in Zenith',
        body: 'Enter all four fields below, or skip and complete later in Settings — your storage connection is not affected.',
      },
    ],
  },
};

export function getSetupGuide(tier) {
  return BYOC_SETUP_GUIDES[tier] || null;
}
