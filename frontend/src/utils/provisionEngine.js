/**
 * Resolve provision engine label for a deployment record (API or detail).
 * Internal API values: boto3 (AWS fast path), sdk (GCP/Azure fast path), terraform.
 */
export function getProvisionEngine(dep) {
  if (!dep) return 'boto3';
  const raw = dep.provision_engine;
  if (raw === 'boto3' || raw === 'terraform' || raw === 'sdk') return raw;
  if (dep.fast_path) {
    const csp = (dep.config?.csp || dep.csp || 'AWS').toUpperCase();
    return csp === 'AWS' ? 'boto3' : 'sdk';
  }
  return 'terraform';
}

export function isFastPathEngine(engine) {
  return engine === 'boto3' || engine === 'sdk';
}

/** Per-cloud SDK name — use when the selected provider is known (detail panels, plan output). */
export function getFastPathLabel(csp = 'AWS') {
  const normalized = String(csp || 'AWS').toUpperCase();
  if (normalized === 'AWS') return 'AWS SDK (Boto3)';
  if (normalized === 'GCP') return 'Google Cloud SDK';
  if (normalized === 'AZURE') return 'Azure SDK';
  return 'Cloud SDK';
}

/** User preference toggle — generic label (status bar, wizard header). */
export function getEffectiveEngineLabel(preference) {
  if (preference === 'terraform') return 'Terraform';
  return 'Cloud SDK';
}

export function getEngineLabel(engine, csp = 'AWS') {
  if (engine === 'terraform') return 'Terraform';
  if (isFastPathEngine(engine)) return getFastPathLabel(csp);
  return 'Terraform';
}

export function getLoadingMessage(action, engine, csp = 'AWS') {
  const cloudAccount = 'your cloud account';
  const fastLabel = isFastPathEngine(engine) ? getFastPathLabel(csp) : 'Terraform';
  const messages = {
    drift: isFastPathEngine(engine)
      ? `Checking drift against ${cloudAccount}… ${fastLabel} is comparing live resources to your saved stack.`
      : `Checking drift against ${cloudAccount}… Terraform is comparing live state to your stack. This can take up to a minute.`,
    'remediate-preview': isFastPathEngine(engine)
      ? `Checking what would change if ${fastLabel} re-applies your stack…`
      : 'Running Terraform plan to preview fixes…',
    'remediate-apply': isFastPathEngine(engine)
      ? `Re-applying your stack with ${fastLabel} to restore desired state…`
      : 'Applying Terraform to restore desired state…',
    destroy: 'Destroying cloud infrastructure…',
    detail: 'Loading deployment details…',
    delete: 'Updating deployment list…',
  };
  return messages[action] || 'Working…';
}

export function getRemediateConfirmMessage(engine, csp = 'AWS') {
  if (engine === 'terraform') {
    return 'Run Terraform apply to restore desired state?';
  }
  return `Re-apply this stack with ${getFastPathLabel(csp)} to restore the desired state?`;
}
