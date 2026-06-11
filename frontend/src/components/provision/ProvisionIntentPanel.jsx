import React from "react";
import WorkloadGuidancePanel from "../vm/WorkloadGuidancePanel.jsx";

/**
 * Step 0 — plain-English workload intent for infrastructure provisioning.
 */
export default function ProvisionIntentPanel({
  workloadDescription,
  onWorkloadChange,
  analysis,
  isAnalyzing,
  followUpAnswers,
  onFollowUpChange,
}) {
  return (
    <div className="provision-intent-panel">
      <div className="section-header">
        <h3>What do you want to build?</h3>
        <p>Describe your goal in everyday language. We&apos;ll suggest the right cloud stack.</p>
      </div>
      <div className="config-field">
        <label htmlFor="provision-workload-description">Your goal</label>
        <textarea
          id="provision-workload-description"
          className="provision-intent-textarea"
          rows={5}
          value={workloadDescription}
          onChange={(e) => onWorkloadChange(e.target.value)}
          placeholder="e.g. I need a small API server for a Node.js app with a PostgreSQL database"
        />
      </div>
      <WorkloadGuidancePanel
        analysis={analysis}
        isAnalyzing={isAnalyzing}
        followUpAnswers={followUpAnswers}
        onFollowUpChange={onFollowUpChange}
      />
      {analysis?.recommendation && (
        <div className="provision-intent-recommendation">
          <strong>Suggested stack:</strong>{" "}
          {analysis.recommendation.template.replace("-", " ")}{" "}
          <span className="provision-intent-confidence">
            ({analysis.recommendation.confidence}% confidence)
          </span>
          {analysis.auto_apply_eligible && (
            <p className="provision-intent-ready">
              Template modules are pre-selected — continue to compare clouds.
            </p>
          )}
          <ul className="provision-intent-reasons">
            {(analysis.recommendation.reasons || []).slice(0, 3).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
