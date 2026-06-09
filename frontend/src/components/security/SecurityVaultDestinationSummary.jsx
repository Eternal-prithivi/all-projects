import React, { useEffect, useState } from "react";
import { apiClient } from "../../api";
import { formatRegionLabel } from "../../hooks/useAwsBuckets";
import { CSP_LABELS } from "../../hooks/useCloudAvailability";
import BucketRegionSelector from "../BucketRegionSelector";
import GcpBucketSelector from "../GcpBucketSelector";
import AzureContainerSelector from "../AzureContainerSelector";
import "../../styles/security-page.css";

const CSP_ICONS = {
  AWS: "/images/aws.png",
  GCP: "/images/google-cloud_logo.png",
  Azure: "/images/Microsoft_Azure.png",
};

function sourceLabel(source) {
  return source === "byoc" ? "Your account (BYOC)" : "Zenith platform";
}

function formatRegion(code) {
  if (!code || code === "—") return null;
  return formatRegionLabel(code) || code;
}

function VaultDestinationCards({ showProviders, targets }) {
  return (
    <div className="security-vault-summary-grid">
      {showProviders.map((csp) => {
        const entry = targets?.targets?.[csp];
        const vault = entry?.security;
        if (!vault) return null;
        const regionLabel = formatRegion(vault.region);
        const bucketLabel = vault.account
          ? `${vault.account} / ${vault.bucket}`
          : vault.bucket;

        return (
          <article key={csp} className="security-vault-summary-card">
            <div className="security-vault-summary-card-head">
              <img
                src={CSP_ICONS[csp]}
                alt=""
                width={22}
                height={22}
                className="security-vault-summary-icon"
              />
              <div>
                <h4>{CSP_LABELS[csp] || csp}</h4>
                <span className="security-vault-summary-source">
                  {sourceLabel(entry.credential_source)}
                </span>
              </div>
            </div>
            <dl className="security-vault-summary-details">
              <div>
                <dt>Primary vault</dt>
                <dd>
                  <code>{bucketLabel}</code>
                  {regionLabel ? ` · ${regionLabel}` : ""}
                </dd>
              </div>
              <div>
                <dt>Path</dt>
                <dd>
                  <code>{vault.key_prefix}</code>
                </dd>
              </div>
              {vault.replica_bucket && vault.secure_dual_write && (
                <div>
                  <dt>Replica (backup only)</dt>
                  <dd>
                    <code>{vault.replica_bucket}</code>
                    {formatRegion(vault.replica_region)
                      ? ` · ${formatRegion(vault.replica_region)}`
                      : ""}
                  </dd>
                </div>
              )}
            </dl>
          </article>
        );
      })}
    </div>
  );
}

/**
 * Platform: collapsible vault info only. BYOC/hybrid: per-cloud vault pickers + optional disclosure.
 */
export default function SecurityVaultDestinationSummary({
  providers = [],
  activeCsp = "ALL",
  credentialMode = "platform",
  reloadToken = 0,
  selectedBucket,
  selectedRegion = "all",
  onBucketChange,
  onRegionChange,
  onPrimaryVaultResolved,
}) {
  const [targets, setTargets] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const isPlatformOnly = credentialMode === "platform";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await apiClient.get("/byoc/storage-targets");
        if (!cancelled) {
          setTargets(res.data);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("Could not load vault destinations.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  useEffect(() => {
    if (!targets || !onPrimaryVaultResolved || credentialMode === "platform") return;
    for (const csp of ["AWS", "GCP", "Azure"]) {
      const entry = targets.targets?.[csp];
      const vault = entry?.security;
      if (entry?.credential_source === "byoc" && vault?.bucket) {
        onPrimaryVaultResolved(vault.bucket, vault.region || null, csp);
      }
    }
  }, [targets, onPrimaryVaultResolved, credentialMode]);

  const showProviders = providers.filter(
    (csp) => activeCsp === "ALL" || activeCsp === csp
  );

  const awsEntry = targets?.targets?.AWS;
  const gcpEntry = targets?.targets?.GCP;
  const azureEntry = targets?.targets?.Azure;

  const showByocAwsPicker =
    awsEntry?.credential_source === "byoc" &&
    providers.includes("AWS") &&
    (activeCsp === "ALL" || activeCsp === "AWS");

  const showByocGcpPicker =
    gcpEntry?.credential_source === "byoc" &&
    providers.includes("GCP") &&
    (activeCsp === "ALL" || activeCsp === "GCP");

  const showByocAzurePicker =
    azureEntry?.credential_source === "byoc" &&
    providers.includes("Azure") &&
    (activeCsp === "ALL" || activeCsp === "Azure");

  if (loading && !isPlatformOnly) {
    return (
      <section className="security-vault-summary" aria-label="Secure vault destinations">
        <p className="security-vault-summary-loading">Loading vault destinations…</p>
      </section>
    );
  }

  if (loading && isPlatformOnly) {
    return null;
  }

  const modeHint =
    targets?.mode === "hybrid"
      ? "Hybrid — BYOC plus Zenith platform vaults"
      : targets?.mode === "byoc"
        ? "Your connected cloud accounts"
        : "Fixed per cloud by your administrator — not chosen per upload";

  const vaultDisclosure = (
    <details className="security-vault-disclosure">
      <summary className="security-vault-disclosure-summary">Vault storage locations</summary>
      <div className="security-vault-disclosure-body">
        <p className="security-vault-disclosure-hint">{modeHint}</p>
        {error ? (
          <p className="security-vault-summary-error" role="alert">
            {error}
          </p>
        ) : (
          <VaultDestinationCards showProviders={showProviders} targets={targets} />
        )}
      </div>
    </details>
  );

  if (isPlatformOnly) {
    return (
      <section className="security-vault-dest security-vault-dest--platform" aria-label="Vault info">
        {vaultDisclosure}
      </section>
    );
  }

  const hasByocPicker = showByocAwsPicker || showByocGcpPicker || showByocAzurePicker;

  return (
    <section className="security-vault-dest security-vault-dest--byoc" aria-label="Secure vault destinations">
      {hasByocPicker && (
        <div className="security-vault-summary-byoc">
          {showByocAwsPicker && (
            <>
              <p className="security-vault-summary-byoc-hint">
                BYOC AWS — pick the bucket to sync and filter your vault files.
              </p>
              <BucketRegionSelector
                surface="security"
                storageKeyPrefix="zenith.security"
                selectedBucket={selectedBucket}
                selectedRegion={selectedRegion}
                onBucketChange={onBucketChange}
                onRegionChange={onRegionChange}
                reloadToken={reloadToken}
              />
            </>
          )}
          {showByocGcpPicker && (
            <>
              <p className="security-vault-summary-byoc-hint">
                BYOC GCP — pick the secure vault bucket to sync and filter your files.
              </p>
              <GcpBucketSelector
                surface="security"
                storageKeyPrefix="zenith.security"
                selectedBucket={selectedBucket}
                onBucketChange={onBucketChange}
                reloadToken={reloadToken}
              />
            </>
          )}
          {showByocAzurePicker && (
            <>
              <p className="security-vault-summary-byoc-hint">
                BYOC Azure — pick the secure vault container to sync and filter your files.
              </p>
              <AzureContainerSelector
                surface="security"
                storageKeyPrefix="zenith.security"
                selectedContainer={selectedBucket}
                onContainerChange={(name) => onBucketChange(name, null)}
                reloadToken={reloadToken}
              />
            </>
          )}
        </div>
      )}
      {vaultDisclosure}
    </section>
  );
}
