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
        className="workload-guidance--provision"
        title="Description quality"
        idleHint="Describe your goal above — we'll score how clear your request is and highlight what's missing."
        analysis={analysis}
        isAnalyzing={isAnalyzing}
        followUpAnswers={followUpAnswers}
        onFollowUpChange={onFollowUpChange}
      />
      {analysis?.recommendation && (
        <div className="provision-intent-recommendation">
          <div className="provision-intent-recommendation__header">
            <strong>Suggested stack:</strong>{" "}
            {analysis.recommendation.template.replace(/-/g, " ")}{" "}
            <span className="provision-intent-confidence">
              ({analysis.recommendation.confidence}% confidence)
            </span>
          </div>

          {(analysis.recommendation.suggested_modules || []).length > 0 && (
            <div className="provision-intent-modules">
              <span className="provision-intent-modules__label">Suggested modules</span>
              <ul className="provision-intent-modules__list">
                {analysis.recommendation.suggested_modules.map((mod) => (
                  <li key={mod.key} className="provision-intent-module">
                    <span className="provision-intent-module__name">{mod.name}</span>
                    {mod.reason && (
                      <span className="provision-intent-module__reason">{mod.reason}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {analysis.auto_apply_eligible && (
            <p className="provision-intent-ready">
              Modules are pre-selected — continue to compare clouds or customize on the next step.
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
