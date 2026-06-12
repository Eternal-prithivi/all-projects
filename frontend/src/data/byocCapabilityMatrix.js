/** Per-CSP feature availability after storage-only BYOC connect. */

export const BYOC_FEATURE_LABELS = {
  storage: 'Storage',
  security: 'Security',
  vm: 'VMs',
  provision: 'Provision',
  cost: 'Cost',
};

export const BYOC_CAPABILITY_MATRIX = {
  AWS: {
    worksAfterStorageOnly: ['storage', 'security', 'vm', 'provision', 'cost'],
    blockedUntilTier2: [],
    tier2Label: null,
  },
  GCP: {
    worksAfterStorageOnly: ['storage', 'security', 'vm', 'provision'],
    blockedUntilTier2: ['cost'],
    tier2Label: 'BigQuery billing export',
  },
  Azure: {
    worksAfterStorageOnly: ['storage', 'security'],
    blockedUntilTier2: ['vm', 'provision', 'cost'],
    tier2Label: 'Service principal',
  },
};

export function formatFeatureList(keys) {
  return keys.map((k) => BYOC_FEATURE_LABELS[k] || k).join(', ');
}
