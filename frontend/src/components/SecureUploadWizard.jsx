import React, { useEffect, useMemo, useState } from "react";
import { CSP_LABELS } from "../hooks/useCloudAvailability";
import { scanSecureFile } from "../api";
import { isClientPasswordValid } from "../utils/passwordPolicy";
import BucketRegionSelector from "./BucketRegionSelector";
import SecurityCostPreview from "./security/SecurityCostPreview";
import SecurityVaultDestinationSummary from "./security/SecurityVaultDestinationSummary";
import ZenithWizardFrame, { WizardNote } from "./wizard/ZenithWizardFrame";
import WizardPasswordFields from "./wizard/WizardPasswordFields";
import "../styles/encryption-modal.css";

const STEP_LABELS = ["Scan", "Encrypt", "Folder", "Replicate", "Review"];

const ENCRYPTION_NOTES = {
  "server-side": (
    <>
      Zenith uploads your file to the secure vault using your cloud&apos;s managed encryption
      (AES-256). You do not need a password. Zenith operators with cloud access could read
      plaintext depending on your cloud IAM policies.
    </>
  ),
  "client-side": (
    <>
      Your browser encrypts the file before any bytes leave your device. The password is never
      sent to Zenith. If you lose the password, the file cannot be recovered.
    </>
  ),
  none: (
    <>
      The file is stored in your 2FA-protected vault without Zenith-managed encryption. Anyone
      with vault or cloud access could read plaintext. Not recommended when sensitive data was
      detected.
    </>
  ),
};

export default function SecureUploadWizard({
  file,
  token,
  providers = [],
  selectedBucket,
  selectedRegion,
  onBucketChange,
  onRegionChange,
  onClose,
  onComplete,
  isSubmitting = false,
  securityPrefs = null,
  awsBucketPickerEnabled = false,
}) {
  const [step, setStep] = useState(0);
  const [scanning, setScanning] = useState(true);
  const [scan, setScan] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [encryptionMethod, setEncryptionMethod] = useState(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [enableReplication, setEnableReplication] = useState(false);
  const [targetCsp, setTargetCsp] = useState(
    securityPrefs?.default_security_csp || providers[0] || "AWS",
  );
  const [skipEncryptionAcknowledged, setSkipEncryptionAcknowledged] = useState(false);

  const fileSizeMb = useMemo(() => {
    const bytes = scan?.size_bytes || file?.size || 0;
    return Math.max(bytes / (1024 * 1024), 0.001);
  }, [scan, file]);

  const isSensitive = scan?.is_sensitive ?? true;
  const replicationSupported = targetCsp === "AWS" || targetCsp === "GCP" || targetCsp === "Azure";

  useEffect(() => {
    if (!securityPrefs) return;
    const prefCsp = securityPrefs.default_security_csp;
    if (prefCsp && providers.includes(prefCsp)) {
      setTargetCsp(prefCsp);
    }
    if (securityPrefs.default_security_replication) {
      setEnableReplication(true);
    }
    const enc = securityPrefs.default_security_encryption;
    if (enc === "server-side" || enc === "client-side") {
      setEncryptionMethod(enc);
    }
  }, [securityPrefs, providers]);

  useEffect(() => {
    if (providers.length && !providers.includes(targetCsp)) {
      setTargetCsp(providers[0]);
    }
  }, [providers, targetCsp]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!file || !token) return;
      setScanning(true);
      setScanError(null);
      try {
        const result = await scanSecureFile(file, token);
        if (!cancelled) setScan(result);
      } catch (err) {
        if (!cancelled) {
          setScanError(err.detail || err.message || "Scan failed");
        }
      } finally {
        if (!cancelled) setScanning(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [file, token]);

  const reasonText =
    scan?.scan_reasons?.length > 0
      ? scan.scan_reasons.map((r) => r.replace(/_/g, " ")).join(", ")
      : "patterns associated with credentials or PII";

  const stepCanAdvance = useMemo(() => {
    if (step === 0) return !scanning && !scanError;
    if (step === 1) {
      if (!encryptionMethod) return false;
      if (encryptionMethod === "none") {
        return !isSensitive || skipEncryptionAcknowledged;
      }
      if (encryptionMethod === "client-side") {
        return isClientPasswordValid(password, confirmPassword);
      }
      return true;
    }
    if (step === 2) {
      const needsAwsBucket = targetCsp === "AWS" && awsBucketPickerEnabled;
      return Boolean(targetCsp) && (!needsAwsBucket || selectedBucket);
    }
    if (step === 3) return true;
    return true;
  }, [
    step,
    scanning,
    scanError,
    encryptionMethod,
    password,
    confirmPassword,
    targetCsp,
    selectedBucket,
    awsBucketPickerEnabled,
    isSensitive,
    skipEncryptionAcknowledged,
  ]);

  const nextBlockedHint = useMemo(() => {
    if (step !== 1 || stepCanAdvance) return null;
    if (!encryptionMethod) return "Select an encryption option to continue.";
    if (encryptionMethod === "none" && isSensitive && !skipEncryptionAcknowledged) {
      return "Confirm you accept storing sensitive content without encryption.";
    }
    if (encryptionMethod === "client-side") {
      if (!password || !confirmPassword) {
        return "Enter and confirm your encryption password.";
      }
      if (!isClientPasswordValid(password, confirmPassword)) {
        if (password !== confirmPassword) {
          return "Passwords must match before you can continue.";
        }
        return "Meet all password requirements above (strength bar must show Strong).";
      }
    }
    return null;
  }, [step, stepCanAdvance, encryptionMethod, password, confirmPassword, isSensitive, skipEncryptionAcknowledged]);

  const nextStep = () => {
    if (step < STEP_LABELS.length - 1 && stepCanAdvance) setStep((s) => s + 1);
  };

  const footer = (
    <>
      {nextBlockedHint && (
        <p className="zenith-wizard-footer-hint" role="status">
          {nextBlockedHint}
        </p>
      )}
      <button type="button" className="zenith-wizard-btn" onClick={onClose} disabled={isSubmitting}>
        Cancel
      </button>
      {step > 0 && (
        <button
          type="button"
          className="zenith-wizard-btn"
          onClick={() => setStep((s) => s - 1)}
          disabled={isSubmitting}
        >
          ← Back
        </button>
      )}
      {step < STEP_LABELS.length - 1 ? (
        <button
          type="button"
          className="zenith-wizard-btn zenith-wizard-btn--primary"
          onClick={nextStep}
          disabled={!stepCanAdvance || isSubmitting}
        >
          Next →
        </button>
      ) : (
        <button
          type="button"
          className="zenith-wizard-btn zenith-wizard-btn--primary"
          disabled={isSubmitting || !stepCanAdvance}
          onClick={() =>
            onComplete({
              encryptionMethod,
              password: encryptionMethod === "client-side" ? password : null,
              csp: targetCsp,
              enableReplication: replicationSupported && enableReplication,
              bucket: selectedBucket,
              isSensitive,
            })
          }
        >
          {isSubmitting ? "Uploading…" : "Upload to secure vault"}
        </button>
      )}
    </>
  );

  return (
    <ZenithWizardFrame
      title="Secure file upload"
      subtitle={file?.name ? `Configuring ${file.name}` : "Step-by-step vault upload"}
      stepLabels={STEP_LABELS}
      currentStep={step}
      onStepClick={(i) => i < step && setStep(i)}
      onClose={onClose}
      footer={footer}
    >
      {step === 0 && (
        <div>
          <h3 className="zenith-wizard-section-title">Scan results</h3>
          <p className="zenith-wizard-section-desc">
            We inspect file content for sensitive patterns before anything is stored.
          </p>
          {scanning && <p className="zenith-wizard-section-desc">Scanning…</p>}
          {scanError && (
            <WizardNote title="Scan error" variant="warn">
              {scanError}
            </WizardNote>
          )}
          {!scanning && scan && (
            <>
              <WizardNote
                title={isSensitive ? "Sensitive content detected" : "No sensitive patterns"}
                variant={isSensitive ? "warn" : "success"}
              >
                {isSensitive ? (
                  <p>
                    Found: <strong>{reasonText}</strong>. Choose encryption (recommended), or
                    explicitly skip encryption if you accept the risk.
                  </p>
                ) : (
                  <p>
                    No sensitive patterns found. You may skip encryption or enable it in the next
                    step.
                  </p>
                )}
              </WizardNote>
              <div className="zenith-wizard-review">
                <dt>File</dt>
                <dd>{file?.name}</dd>
                <dt>Size</dt>
                <dd>{((scan.size_bytes || file?.size || 0) / 1024).toFixed(2)} KB</dd>
                {scan.ml_scan_score != null && (
                  <>
                    <dt>ML risk score</dt>
                    <dd>{Math.round(scan.ml_scan_score * 100)}%</dd>
                  </>
                )}
              </div>
              {scan.ml_scan_score != null && scan.ml_scan_score >= 0.65 && !isSensitive && (
                <WizardNote title="ML-assisted scan" variant="warn">
                  The ML risk model also flagged this file. Consider encryption even if rules were
                  quiet.
                </WizardNote>
              )}
            </>
          )}
          <WizardNote title="What happens next">
            Next you choose encryption, target cloud (AWS, Google Cloud, or Azure), optional
            replication, then upload.
          </WizardNote>
        </div>
      )}

      {step === 1 && (
        <div>
          <h3 className="zenith-wizard-section-title">Choose encryption</h3>
          <p className="zenith-wizard-section-desc">
            Pick cloud-managed encryption or browser encryption before upload.
          </p>
          <div className="zenith-wizard-option-grid">
            <div
              className={`zenith-wizard-option-card${
                encryptionMethod === "server-side" ? " is-selected" : ""
              }`}
              onClick={() => setEncryptionMethod("server-side")}
              onKeyDown={(e) => e.key === "Enter" && setEncryptionMethod("server-side")}
              role="button"
              tabIndex={0}
            >
              <h4>
                <input type="radio" readOnly checked={encryptionMethod === "server-side"} />
                Cloud-managed encryption
              </h4>
              <p>AWS SSE, GCS, or Azure encrypt-at-rest using provider keys.</p>
            </div>
            <div
              className={`zenith-wizard-option-card${
                encryptionMethod === "client-side" ? " is-selected" : ""
              }`}
              onClick={() => setEncryptionMethod("client-side")}
              onKeyDown={(e) => e.key === "Enter" && setEncryptionMethod("client-side")}
              role="button"
              tabIndex={0}
            >
              <h4>
                <input type="radio" readOnly checked={encryptionMethod === "client-side"} />
                Zenith browser encryption
              </h4>
              <p>Zero-knowledge — encrypted locally, then uploaded as ciphertext.</p>
            </div>
            <div
              className={`zenith-wizard-option-card${
                encryptionMethod === "none" ? " is-selected" : ""
              }${isSensitive ? " zenith-wizard-option-card--warn" : ""}`}
              onClick={() => setEncryptionMethod("none")}
              onKeyDown={(e) => e.key === "Enter" && setEncryptionMethod("none")}
              role="button"
              tabIndex={0}
            >
              <h4>
                <input type="radio" readOnly checked={encryptionMethod === "none"} />
                Store without encryption
              </h4>
              <p>
                Upload to the secure vault with 2FA only — no Zenith encryption layer.
                {isSensitive ? " Not recommended for sensitive files." : ""}
              </p>
            </div>
          </div>
          {encryptionMethod === "none" && isSensitive && (
            <label className="security-skip-encrypt-ack">
              <input
                type="checkbox"
                checked={skipEncryptionAcknowledged}
                onChange={(e) => setSkipEncryptionAcknowledged(e.target.checked)}
              />
              <span>
                I understand this file contains sensitive data and I accept storing it without
                Zenith encryption.
              </span>
            </label>
          )}
          {encryptionMethod && (
            <WizardNote title="If you continue with this option">
              {ENCRYPTION_NOTES[encryptionMethod]}
            </WizardNote>
          )}
          {encryptionMethod === "client-side" && (
            <WizardPasswordFields
              password={password}
              confirmPassword={confirmPassword}
              onPasswordChange={setPassword}
              onConfirmChange={setConfirmPassword}
            />
          )}
          {encryptionMethod && token && (
            <SecurityCostPreview
              token={token}
              fileSizeMb={fileSizeMb}
              encryptionMethod={encryptionMethod}
              selectedCsp={targetCsp}
              enableReplication={false}
              compact
            />
          )}
        </div>
      )}

      {step === 2 && (
        <div className="zenith-wizard-destination">
          <h3 className="zenith-wizard-section-title">Cloud & folder</h3>
          <p className="zenith-wizard-section-desc">
            Choose where this file is stored. Lists platform clouds from server configuration and
            any BYOC connections from Settings.
          </p>
          {providers.length === 0 ? (
            <WizardNote title="No clouds available" variant="warn">
              Configure AWS, Google Cloud, or Azure in server .env, or connect BYOC under Settings.
            </WizardNote>
          ) : (
            <>
              <div className="zenith-wizard-option-grid">
                {providers.map((p) => (
                  <div
                    key={p}
                    className={`zenith-wizard-option-card${
                      targetCsp === p ? " is-selected" : ""
                    }`}
                    onClick={() => setTargetCsp(p)}
                    role="button"
                    tabIndex={0}
                  >
                    <h4>{CSP_LABELS[p] || p}</h4>
                    <p>Store in your {CSP_LABELS[p] || p} secure vault.</p>
                  </div>
                ))}
              </div>
              {targetCsp === "AWS" && awsBucketPickerEnabled ? (
                <>
                  <WizardNote title="Choose vault folder (S3 bucket)">
                    Select the secure bucket where this file will live.
                  </WizardNote>
                  <BucketRegionSelector
                    surface="security"
                    storageKeyPrefix="zenith.security.wizard"
                    selectedBucket={selectedBucket}
                    selectedRegion={selectedRegion || "all"}
                    onBucketChange={onBucketChange}
                    onRegionChange={onRegionChange}
                  />
                </>
              ) : (
                <SecurityVaultDestinationSummary
                  providers={[targetCsp]}
                  activeCsp={targetCsp}
                />
              )}
              {token && (
                <SecurityCostPreview
                  token={token}
                  fileSizeMb={fileSizeMb}
                  encryptionMethod={encryptionMethod || "server-side"}
                  selectedCsp={targetCsp}
                  enableReplication={false}
                />
              )}
            </>
          )}
        </div>
      )}

      {step === 3 && (
        <div>
          <h3 className="zenith-wizard-section-title">Vault replication</h3>
          <p className="zenith-wizard-section-desc">
            Optional second copy to your platform&apos;s fixed replica bucket or container
            (configured in server .env — no region picker).
          </p>
          <div className="zenith-wizard-replication-row">
            <div className="zenith-wizard-replication-row__text">
              <strong>Replicate secure copy</strong>
              <span>
                {targetCsp === "GCP"
                  ? "Primary GCS secure bucket → fixed replica GCS bucket."
                  : targetCsp === "Azure"
                    ? "Primary secure container → fixed replica container."
                    : "Primary S3 secure bucket → fixed replica S3 bucket."}
              </span>
            </div>
            <label className="zenith-wizard-toggle" aria-label="Enable replication">
              <input
                type="checkbox"
                checked={enableReplication}
                onChange={(e) => setEnableReplication(e.target.checked)}
              />
              <span className="zenith-wizard-toggle__slider" />
            </label>
          </div>
          <WizardNote title="If you enable replication">
            Zenith writes to your primary secure vault, then copies to the fixed replica destination
            for {CSP_LABELS[targetCsp] || targetCsp}. Replica location is set by your operator in
            server configuration — not chosen per upload.
          </WizardNote>
          {!enableReplication && (
            <WizardNote title="If you skip replication">
              Only the primary secure vault location receives the file. You can enable replication
              later only by re-uploading with replication turned on.
            </WizardNote>
          )}
          {token && (
            <SecurityCostPreview
              token={token}
              fileSizeMb={fileSizeMb}
              encryptionMethod={encryptionMethod || "server-side"}
              selectedCsp={targetCsp}
              enableReplication={enableReplication && replicationSupported}
            />
          )}
        </div>
      )}

      {step === 4 && (
        <div>
          <h3 className="zenith-wizard-section-title">Review & upload</h3>
          <p className="zenith-wizard-section-desc">Confirm choices before writing to the vault.</p>
          <dl className="zenith-wizard-review">
            <dt>File</dt>
            <dd>{file?.name}</dd>
            <dt>Sensitive scan</dt>
            <dd>{isSensitive ? `Yes (${reasonText})` : "No"}</dd>
            <dt>Encryption</dt>
            <dd>
              {encryptionMethod === "client-side"
                ? "Browser (zero-knowledge)"
                : encryptionMethod === "none"
                  ? "None (vault + 2FA only)"
                  : "Cloud-managed"}
            </dd>
            <dt>Replication</dt>
            <dd>
              {enableReplication && replicationSupported
                ? `Fixed replica (${CSP_LABELS[targetCsp] || targetCsp})`
                : "None"}
            </dd>
            <dt>Cloud</dt>
            <dd>{CSP_LABELS[targetCsp] || targetCsp}</dd>
            {targetCsp === "AWS" && selectedBucket && (
              <>
                <dt>Vault bucket</dt>
                <dd>
                  <code>{selectedBucket}</code>
                </dd>
              </>
            )}
          </dl>
          <WizardNote title="On upload">
            Zenith will{" "}
            {encryptionMethod === "client-side"
              ? "store ciphertext"
              : encryptionMethod === "none"
                ? "store the file without Zenith encryption"
                : "encrypt at rest"}{" "}
            in your {CSP_LABELS[targetCsp] || targetCsp} vault
            {enableReplication && replicationSupported ? " with a replica copy" : ""}. This action
            cannot be undone without deleting the file from the vault.
          </WizardNote>
          {token && (
            <SecurityCostPreview
              token={token}
              fileSizeMb={fileSizeMb}
              encryptionMethod={encryptionMethod || "server-side"}
              selectedCsp={targetCsp}
              enableReplication={enableReplication && replicationSupported}
            />
          )}
        </div>
      )}
    </ZenithWizardFrame>
  );
}
