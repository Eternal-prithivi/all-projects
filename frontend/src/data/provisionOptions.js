/** IAM role presets and EC2 OS options — keys must match backend provision_config_options.py */

export const IAM_ROLE_PRESETS = [
  {
    id: 's3_read_only',
    label: 'S3 read only',
    description: 'List and download objects from your stack S3 bucket (default).',
  },
  {
    id: 's3_read_write',
    label: 'S3 read & write',
    description: 'Upload, download, and delete objects in your stack S3 bucket.',
  },
  {
    id: 'ssm_session',
    label: 'SSM Session Manager',
    description: 'Connect via AWS Session Manager — no SSH keys required.',
  },
  {
    id: 's3_read_ssm',
    label: 'S3 read + SSM',
    description: 'Read S3 objects and use Session Manager for shell access.',
  },
  {
    id: 'dynamodb_app',
    label: 'DynamoDB app access',
    description: 'Read/write your stack DynamoDB table (enable DynamoDB module).',
  },
  {
    id: 'minimal',
    label: 'Trust only (no AWS API access)',
    description: 'Role with no permissions — add policies later in AWS console.',
  },
];

export const EC2_OS_IMAGES = [
  {
    id: 'amazon_linux_2',
    label: 'Amazon Linux 2',
    description: 'Stable default for most apps (yum).',
  },
  {
    id: 'amazon_linux_2023',
    label: 'Amazon Linux 2023',
    description: 'Newer Amazon Linux with long-term support.',
  },
  {
    id: 'ubuntu_22_04',
    label: 'Ubuntu 22.04 LTS',
    description: 'Popular Ubuntu LTS (apt).',
  },
  {
    id: 'ubuntu_24_04',
    label: 'Ubuntu 24.04 LTS',
    description: 'Latest Ubuntu LTS.',
  },
];

export const EC2_USER_DATA_PLACEHOLDER = `#!/bin/bash
# Optional — runs once on first boot. Example:
# yum update -y
# yum install -y docker git
# systemctl enable --now docker
`;

export const GCP_SA_PRESETS = [
  {
    id: 'gcs_read_only',
    label: 'GCS read only',
    description: 'List and download objects from your stack GCS bucket (default).',
  },
  {
    id: 'gcs_read_write',
    label: 'GCS read & write',
    description: 'Upload, download, and delete objects in your stack bucket.',
  },
  {
    id: 'firestore_app',
    label: 'Firestore app access',
    description: 'Read/write Firestore data (enable Firestore module).',
  },
  {
    id: 'logging_writer',
    label: 'Cloud Logging writer',
    description: 'Write application logs to Cloud Logging.',
  },
  {
    id: 'gcs_read_logging',
    label: 'GCS read + Logging',
    description: 'Read GCS objects and write logs.',
  },
  {
    id: 'minimal',
    label: 'Service account only (no roles)',
    description: 'Create SA for attachment — grant roles later in GCP console.',
  },
];

export const GCE_OS_IMAGES = [
  { id: 'debian_12', label: 'Debian 12', description: 'Default stable image for GCE.' },
  { id: 'ubuntu_22_04', label: 'Ubuntu 22.04 LTS', description: 'Ubuntu LTS (apt).' },
  { id: 'ubuntu_24_04', label: 'Ubuntu 24.04 LTS', description: 'Latest Ubuntu LTS.' },
  {
    id: 'cos_stable',
    label: 'Container-Optimized OS',
    description: 'Google COS — ideal for Docker/Kubernetes workloads.',
  },
];

export const AZURE_IDENTITY_PRESETS = [
  {
    id: 'storage_blob_read',
    label: 'Blob Storage read',
    description: 'Read blobs in your stack storage account (default).',
  },
  {
    id: 'storage_blob_contributor',
    label: 'Blob Storage read & write',
    description: 'Read, write, and delete blobs in your storage account.',
  },
  {
    id: 'cosmos_data_contributor',
    label: 'Cosmos DB access',
    description: 'Manage Cosmos DB account resources (enable Cosmos module).',
  },
  {
    id: 'minimal',
    label: 'Managed identity only (no roles)',
    description: 'System-assigned identity with no RBAC — assign roles later.',
  },
];

export const AZURE_OS_IMAGES = [
  {
    id: 'ubuntu_22_04',
    label: 'Ubuntu 22.04 LTS',
    description: 'Canonical Ubuntu Jammy (default).',
  },
  { id: 'ubuntu_24_04', label: 'Ubuntu 24.04 LTS', description: 'Canonical Ubuntu Noble.' },
  { id: 'debian_12', label: 'Debian 12', description: 'Debian bookworm.' },
  { id: 'azure_linux', label: 'Azure Linux 3', description: 'Microsoft Azure Linux image.' },
];

export const VM_STARTUP_SCRIPT_PLACEHOLDER = `#!/bin/bash
# Optional — runs once on first boot. Example:
# apt-get update -y
# apt-get install -y docker.io git
# systemctl enable --now docker
`;
