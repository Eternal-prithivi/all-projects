/**
 * Resolve provision engine label for a deployment record (API or detail).
 */
export function getProvisionEngine(dep) {
  if (!dep) return 'boto3';
  const raw = dep.provision_engine;
  if (raw === 'boto3' || raw === 'terraform') return raw;
  if (dep.fast_path) return 'boto3';
  return 'terraform';
}

export function getEngineLabel(engine) {
  return engine === 'terraform' ? 'Terraform' : 'Boto3';
}

export function getLoadingMessage(action, engine) {
  const messages = {
    drift:
      engine === 'boto3'
        ? 'Checking drift against your AWS account… Boto3 is comparing live resources to your saved stack.'
        : 'Checking drift against your AWS account… Terraform is comparing live state to your stack. This can take up to a minute.',
    'remediate-preview':
      engine === 'boto3'
        ? 'Checking what would change if Boto3 re-applies your stack…'
        : 'Running Terraform plan to preview fixes…',
    'remediate-apply':
      engine === 'boto3'
        ? 'Re-applying your stack with Boto3 to restore desired state…'
        : 'Applying Terraform to restore desired state…',
    destroy: 'Destroying infrastructure…',
    detail: 'Loading deployment details…',
    delete: 'Updating deployment list…',
  };
  return messages[action] || 'Working…';
}

export function getRemediateConfirmMessage(engine) {
  if (engine === 'boto3') {
    return 'Re-apply this stack with Boto3 to restore the desired state?';
  }
  return 'Run Terraform apply to restore desired state?';
}
