import React, { useState } from "react";
import BucketRegionSelector from "./BucketRegionSelector";

function CspIcon({ csp }) {
  const icons = {
    AWS: "/images/aws.png",
    GCP: "/images/google-cloud_logo.png",
    Azure: "/images/Microsoft_Azure.png",
  };
  return <img src={icons[csp]} alt={`${csp} logo`} className="csp-icon" />;
}
import ZenithWizardFrame, { WizardNote } from "./wizard/ZenithWizardFrame";
import { CSP_LABELS } from "../hooks/useCloudAvailability";

const STEP_LABELS = ["Analysis", "Cloud", "Folder", "Review"];

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

export default function StorageUploadWizard({
  file,
  recommendation,
  providers = [],
  selectedBucket,
  selectedRegion,
  onBucketChange,
  onRegionChange,
  manualCsp,
  onManualCspChange,
  onClose,
  onConfirmUpload,
  isUploading = false,
}) {
  const recommended = recommendation?.recommendation;
  const [step, setStep] = useState(0);
  const [targetCsp, setTargetCsp] = useState(
    manualCsp ||
      (providers.includes(recommended?.csp) ? recommended.csp : providers[0]) ||
      "AWS"
  );

  const finalCsp =
    manualCsp ||
    (providers.includes(recommended?.csp) ? recommended.csp : providers[0]);

  const canNext = () => {
    if (step === 0) return Boolean(recommendation);
    if (step === 1) return Boolean(targetCsp);
    if (step === 2) return targetCsp !== "AWS" || Boolean(selectedBucket);
    return true;
  };

  const footer = (
    <>
      <button type="button" className="zenith-wizard-btn" onClick={onClose} disabled={isUploading}>
        Cancel
      </button>
      {step > 0 && (
        <button
          type="button"
          className="zenith-wizard-btn"
          onClick={() => setStep((s) => s - 1)}
          disabled={isUploading}
        >
          ← Back
        </button>
      )}
      {step < STEP_LABELS.length - 1 ? (
        <button
          type="button"
          className="zenith-wizard-btn zenith-wizard-btn--primary"
          onClick={() => setStep((s) => s + 1)}
          disabled={!canNext()}
        >
          Next →
        </button>
      ) : (
        <button
          type="button"
          className="zenith-wizard-btn zenith-wizard-btn--primary"
          disabled={isUploading || !canNext()}
          onClick={() => onConfirmUpload(finalCsp)}
        >
          {isUploading ? "Uploading…" : `Upload to ${CSP_LABELS[finalCsp] || finalCsp}`}
        </button>
      )}
    </>
  );

  return (
    <ZenithWizardFrame
      title="Storage placement"
      subtitle={file?.name ? `Where to store ${file.name}` : "ML-guided upload"}
      stepLabels={STEP_LABELS}
      currentStep={step}
      onStepClick={(i) => i < step && setStep(i)}
      onClose={onClose}
      footer={footer}
      className="zenith-wizard-panel--storage"
    >
      {step === 0 && recommendation && (
        <div>
          <h3 className="zenith-wizard-section-title">Analysis results</h3>
          <p className="zenith-wizard-section-desc">
            Zenith classified this file and estimated the most cost-effective storage tier.
          </p>
          <div className="recommendation-box recommendation-box--compact">
            <span className="recommendation-box__label">Recommended tier</span>
            <p className="recommendation-csp">
              <CspIcon csp={recommended.csp} />
              {recommended.csp} — {recommended.service_name}
            </p>
            <p className="zenith-wizard-section-desc" style={{ marginTop: "0.5rem" }}>
              Workload tier: <strong>{recommendation.determined_tier}</strong>
              {recommendation.ensemble_confidence != null &&
                ` · ${formatPercent(recommendation.ensemble_confidence)} ensemble confidence`}
            </p>
          </div>
          <WizardNote title="What happens next">
            You can accept the recommendation or override the cloud on the next step. Then choose
            the bucket or folder prefix, and confirm upload. Billing uses your connected account
            for that cloud.
          </WizardNote>
        </div>
      )}

      {step === 1 && (
        <div>
          <h3 className="zenith-wizard-section-title">Target cloud</h3>
          <p className="zenith-wizard-section-desc">
            Pick where this object will be stored. Only providers available for storage are shown.
          </p>
          <div className="zenith-wizard-option-grid">
            {providers.map((p) => (
              <div
                key={p}
                className={`zenith-wizard-option-card${targetCsp === p ? " is-selected" : ""}`}
                onClick={() => {
                  setTargetCsp(p);
                  onManualCspChange?.(p);
                }}
                role="button"
                tabIndex={0}
              >
                <h4>{CSP_LABELS[p] || p}</h4>
                <p>
                  {p === recommended?.csp
                    ? "Recommended by analysis"
                    : "Override ML recommendation"}
                </p>
              </div>
            ))}
          </div>
          <WizardNote title="If you choose this cloud">
            {targetCsp === recommended?.csp ? (
              <p>
                Upload uses <strong>{recommended.service_name}</strong> on{" "}
                {CSP_LABELS[targetCsp] || targetCsp}, matching the ML tier decision (
                {recommendation.determined_tier}).
              </p>
            ) : (
              <p>
                You are overriding the ML pick ({recommended?.csp}). Zenith still applies the{" "}
                <strong>{recommendation.determined_tier}</strong> tier logic but stores on{" "}
                {CSP_LABELS[targetCsp] || targetCsp} using that provider&apos;s equivalent storage
                class where available.
              </p>
            )}
          </WizardNote>
        </div>
      )}

      {step === 2 && (
        <div className="zenith-wizard-destination">
          <h3 className="zenith-wizard-section-title">Bucket & region</h3>
          <p className="zenith-wizard-section-desc">
            Choose the destination folder for {CSP_LABELS[targetCsp] || targetCsp}.
          </p>
          {targetCsp === "AWS" ? (
            <>
              <WizardNote title="S3 destination">
                Select the bucket (and optional region). Sync after upload refreshes the file table
                for that bucket.
              </WizardNote>
              <BucketRegionSelector
                surface="storage"
                storageKeyPrefix="zenith.storage.wizard"
                selectedBucket={selectedBucket}
                selectedRegion={selectedRegion || "all"}
                onBucketChange={onBucketChange}
                onRegionChange={onRegionChange}
              />
            </>
          ) : (
            <WizardNote title="Provider path">
              Objects upload to your configured {CSP_LABELS[targetCsp] || targetCsp} bucket or
              container from Settings (BYOC or platform). Use Sync to reconcile the file list.
            </WizardNote>
          )}
        </div>
      )}

      {step === 3 && (
        <div>
          <h3 className="zenith-wizard-section-title">Review & upload</h3>
          <dl className="zenith-wizard-review">
            <dt>File</dt>
            <dd>{file?.name}</dd>
            <dt>Tier</dt>
            <dd>{recommendation?.determined_tier}</dd>
            <dt>Cloud</dt>
            <dd>{CSP_LABELS[finalCsp] || finalCsp}</dd>
            <dt>Storage class</dt>
            <dd>
              {recommendation?.options_by_csp?.[finalCsp]?.service_name ||
                recommended?.service_name ||
                "—"}
            </dd>
            {finalCsp === "AWS" && selectedBucket && (
              <>
                <dt>Bucket</dt>
                <dd>
                  <code>{selectedBucket}</code>
                </dd>
              </>
            )}
          </dl>
          <WizardNote title="On upload">
            The file is placed in your {CSP_LABELS[finalCsp] || finalCsp} storage with the selected
            class. Access frequency is tracked for future tier recommendations.
          </WizardNote>
        </div>
      )}
    </ZenithWizardFrame>
  );
}
