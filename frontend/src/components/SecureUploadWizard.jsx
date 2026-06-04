import React, { useEffect, useMemo, useState } from "react";
import { REGION_LABELS } from "../hooks/useAwsBuckets";
import { CSP_LABELS } from "../hooks/useCloudAvailability";
import { scanSecureFile } from "../api";
import { isClientPasswordValid } from "../utils/passwordPolicy";
import BucketRegionSelector from "./BucketRegionSelector";
import ZenithWizardFrame, { WizardNote } from "./wizard/ZenithWizardFrame";
import WizardPasswordFields from "./wizard/WizardPasswordFields";
import "../styles/encryption-modal.css";

const STEP_LABELS = ["Scan", "Encrypt", "Folder", "Replicate", "Review"];

const REPLICATION_REGIONS = [
  { value: "us-east-1", label: "US East (N. Virginia)" },
  { value: "us-west-2", label: "US West (Oregon)" },
  { value: "ap-south-1", label: "Asia Pacific (Mumbai)" },
  { value: "eu-west-1", label: "Europe (Ireland)" },
];

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
}) {
  const [step, setStep] = useState(0);
  const [scanning, setScanning] = useState(true);
  const [scan, setScan] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [encryptionMethod, setEncryptionMethod] = useState(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [enableReplication, setEnableReplication] = useState(false);
  const [replicaRegion, setReplicaRegion] = useState("us-east-1");
  const [targetCsp, setTargetCsp] = useState(providers[0] || "AWS");

  const isSensitive = scan?.is_sensitive ?? true;
  const replicationSupported = targetCsp === "AWS" || targetCsp === "GCP";

  useEffect(() => {
    if (providers.length && !providers.includes(targetCsp)) {
      setTargetCsp(providers[0]);
    }
  }, [providers, targetCsp]);

  useEffect(() => {
    if (targetCsp === "Azure") setEnableReplication(false);
  }, [targetCsp]);

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
      if (encryptionMethod === "client-side") {
        return isClientPasswordValid(password, confirmPassword);
      }
      return true;
    }
    if (step === 2) {
      return Boolean(targetCsp) && (targetCsp !== "AWS" || selectedBucket);
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
  ]);

  const nextBlockedHint = useMemo(() => {
    if (step !== 1 || stepCanAdvance) return null;
    if (!encryptionMethod) return "Select an encryption option to continue.";
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
  }, [step, stepCanAdvance, encryptionMethod, password, confirmPassword]);

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
              replicaRegion: replicationSupported && enableReplication ? replicaRegion : null,
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
                    Found: <strong>{reasonText}</strong>. You must choose encryption, optional
                    replication, and a destination folder before upload.
                  </p>
                ) : (
                  <p>
                    No mandatory encryption wizard is required, but you can still enable
                    encryption in the next steps if you prefer.
                  </p>
                )}
              </WizardNote>
              <div className="zenith-wizard-review">
                <dt>File</dt>
                <dd>{file?.name}</dd>
                <dt>Size</dt>
                <dd>{((scan.size_bytes || file?.size || 0) / 1024).toFixed(2)} KB</dd>
              </div>
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
          </div>
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
              {targetCsp === "AWS" && (
                <>
                  <WizardNote title="Choose vault folder (S3 bucket)">
                    Select the secure bucket (and optional region filter) where this file will
                    live. Replica buckets appear here when configured.
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
              )}
              {targetCsp === "GCP" && (
                <WizardNote title="Google Cloud vault">
                  Uploads use your configured GCS secure bucket. Set{" "}
                  <code>GCP_SERVICE_ACCOUNT_JSON_PATH</code> in server .env (like Azure storage
                  keys). Optional <code>GCP_REPLICA_BUCKET_NAME</code> enables replication on the
                  next step.
                </WizardNote>
              )}
              {targetCsp === "Azure" && (
                <WizardNote title="Azure vault">
                  Files upload to your configured secure container using platform or BYOC
                  credentials from Settings.
                </WizardNote>
              )}
            </>
          )}
        </div>
      )}

      {step === 3 && (
        <div>
          <h3 className="zenith-wizard-section-title">Regional replication</h3>
          <p className="zenith-wizard-section-desc">
            Optional second copy for AWS (cross-region) or Google Cloud (replica bucket).
          </p>
          <div className="zenith-wizard-replication-row">
            <div className="zenith-wizard-replication-row__text">
              <strong>Replicate secure copy</strong>
              <span>
                {replicationSupported
                  ? targetCsp === "GCP"
                    ? "Writes to primary GCS bucket and a configured replica bucket."
                    : "Writes to primary S3 bucket and your replica region."
                  : "Azure stores a single copy in your secure container."}
              </span>
            </div>
            <label className="zenith-wizard-toggle" aria-label="Enable replication">
              <input
                type="checkbox"
                checked={enableReplication}
                onChange={(e) => setEnableReplication(e.target.checked)}
                disabled={!replicationSupported}
              />
              <span className="zenith-wizard-toggle__slider" />
            </label>
          </div>
          {!replicationSupported && (
            <WizardNote title="Note" variant="warn">
              {CSP_LABELS[targetCsp] || targetCsp} does not support vault replication in Zenith yet.
              Choose AWS or Google Cloud on the previous step to enable a replica copy.
            </WizardNote>
          )}
          {enableReplication && replicationSupported && targetCsp === "AWS" && (
            <div className="config-field" style={{ marginTop: "1rem" }}>
              <label htmlFor="secure-replica-region">Replica region (AWS)</label>
              <select
                id="secure-replica-region"
                className="zenith-select"
                value={replicaRegion}
                onChange={(e) => setReplicaRegion(e.target.value)}
              >
                {REPLICATION_REGIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          {enableReplication && replicationSupported && targetCsp === "GCP" && (
            <WizardNote title="Google Cloud replication">
              Zenith copies the object to <code>GCP_REPLICA_BUCKET_NAME</code> when set in server
              configuration. Both buckets must be writable by the same service account.
            </WizardNote>
          )}
          <WizardNote title="If you enable replication">
            {targetCsp === "GCP"
              ? "Zenith stores in your primary GCS secure bucket, then uploads the same object to the replica bucket."
              : `Zenith writes to your primary secure bucket, then copies to the replica bucket in ${
                  REGION_LABELS[replicaRegion] || replicaRegion
                }.`}{" "}
            This increases durability; your cloud bill may include transfer and storage in both
            locations.
          </WizardNote>
          {!enableReplication && (
            <WizardNote title="If you skip replication">
              Only the primary secure vault location receives the file. You can enable replication
              later only by re-uploading with replication turned on.
            </WizardNote>
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
                : "Cloud-managed"}
            </dd>
            <dt>Replication</dt>
            <dd>
              {enableReplication && replicationSupported
                ? targetCsp === "GCP"
                  ? "GCS replica bucket"
                  : REGION_LABELS[replicaRegion] || replicaRegion
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
            Zenith will {encryptionMethod === "client-side" ? "store ciphertext" : "encrypt at rest"}{" "}
            in your {CSP_LABELS[targetCsp] || targetCsp} vault
            {enableReplication && replicationSupported ? " with a replica copy" : ""}. This action
            cannot be undone without deleting the file from the vault.
          </WizardNote>
        </div>
      )}
    </ZenithWizardFrame>
  );
}
