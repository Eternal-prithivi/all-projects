import React, { useState } from "react";
import BucketRegionSelector from "./BucketRegionSelector";
import GcpBucketSelector from "./GcpBucketSelector";
import AzureContainerSelector from "./AzureContainerSelector";
import PlatformRegionPills from "./PlatformRegionPills";

function CspIcon({ csp }) {
  const icons = {
    AWS: "/images/aws.png",
    GCP: "/images/google-cloud_logo.png",
    Azure: "/images/Microsoft_Azure.png",
  };
  return <img src={icons[csp]} alt={`${csp} logo`} className="csp-icon" />;
}
import ZenithWizardFrame, { WizardNote } from "./wizard/ZenithWizardFrame";
import StorageEnsembleBreakdown from "./wizard/StorageEnsembleBreakdown";
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
  selectedGcpBucket,
  onGcpBucketChange,
  selectedAzureContainer,
  onAzureContainerChange,
  platformRegionSlug = null,
  onPlatformRegionChange,
  platformMultiRegion = false,
  platformRegions = [],
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
    if (step === 2) {
      if (platformMultiRegion && !platformRegionSlug) return false;
      if (targetCsp === "AWS") return Boolean(selectedBucket);
      if (targetCsp === "GCP") return Boolean(selectedGcpBucket);
      if (targetCsp === "Azure") return Boolean(selectedAzureContainer);
      return true;
    }
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
            <span className="recommendation-box__label">Recommended placement</span>
            <p className="recommendation-csp">
              <CspIcon csp={recommended.csp} />
              {recommended.csp} — {recommended.service_name}
            </p>
            <p className="zenith-wizard-section-desc recommendation-box__tier-line">
              Workload tier: <strong>{recommendation.determined_tier}</strong>
              {recommendation.ensemble_confidence != null && (
                <>
                  {' '}
                  · <strong>{formatPercent(recommendation.ensemble_confidence)}</strong> ensemble
                  confidence
                </>
              )}
            </p>
          </div>

          <StorageEnsembleBreakdown recommendation={recommendation} />
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
          <h3 className="zenith-wizard-section-title">Region & destination</h3>
          <p className="zenith-wizard-section-desc">
            {platformMultiRegion
              ? "Pick a region, then confirm the bucket or container for this upload."
              : `Choose the destination for ${CSP_LABELS[targetCsp] || targetCsp}.`}
          </p>
          {platformMultiRegion && platformRegions.length > 0 && (
            <PlatformRegionPills
              regions={platformRegions}
              selectedSlug={platformRegionSlug}
              onSelect={onPlatformRegionChange}
              id="wizard-platform-region"
            />
          )}
          {targetCsp === "AWS" && (
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
                platformRegionSlug={platformRegionSlug}
              />
            </>
          )}
          {targetCsp === "GCP" && (
            <>
              <WizardNote title="GCS destination">
                Pick the GCS bucket. Location is fixed per bucket — use Sync after upload to refresh
                the file table.
              </WizardNote>
              <GcpBucketSelector
                storageKeyPrefix="zenith.storage.wizard"
                selectedBucket={selectedGcpBucket}
                onBucketChange={(name) => onGcpBucketChange?.(name)}
                compact
                platformRegionSlug={platformRegionSlug}
              />
            </>
          )}
          {targetCsp === "Azure" && (
            <>
              <WizardNote title="Blob destination">
                Pick the Blob container for this upload. Region follows your storage account.
              </WizardNote>
              <AzureContainerSelector
                storageKeyPrefix="zenith.storage.wizard"
                selectedContainer={selectedAzureContainer}
                onContainerChange={onAzureContainerChange}
                compact
                platformRegionSlug={platformRegionSlug}
              />
            </>
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
            {platformMultiRegion && platformRegionSlug && (
              <>
                <dt>Region</dt>
                <dd>
                  {platformRegions.find((r) => r.slug === platformRegionSlug)?.label ||
                    platformRegionSlug}
                </dd>
              </>
            )}
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
            {finalCsp === "GCP" && selectedGcpBucket && (
              <>
                <dt>GCS bucket</dt>
                <dd>
                  <code>{selectedGcpBucket}</code>
                </dd>
              </>
            )}
            {finalCsp === "Azure" && selectedAzureContainer && (
              <>
                <dt>Container</dt>
                <dd>
                  <code>{selectedAzureContainer}</code>
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
