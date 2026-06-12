import React from "react";

/**
 * Live NLP readiness bar, missing signals, follow-up Q&A, and cluster preview.
 */
function WorkloadGuidancePanel({
  analysis,
  isAnalyzing,
  followUpAnswers,
  onFollowUpChange,
  className = "",
  title = "Prompt readiness for NLP",
  idleHint = "Describe your workload above — we'll show how complete your prompt is and suggest a cluster before you request a VM.",
}) {
  const rootClass = ["workload-guidance", className].filter(Boolean).join(" ");

  if (!analysis && !isAnalyzing) {
    return (
      <div className={`${rootClass} workload-guidance--idle`}>
        <p className="guidance-hint">{idleHint}</p>
      </div>
    );
  }

  if (isAnalyzing && !analysis) {
    return (
      <div className={`${rootClass} workload-guidance--loading`}>
        <p className="guidance-hint">
          <span className="guidance-spinner" aria-hidden="true" />
          Analyzing your description…
        </p>
      </div>
    );
  }

  const readiness = analysis?.readiness || {};
  const score = readiness.readiness_score ?? 0;
  const questions = analysis?.follow_up_questions || [];
  const followUpContext = analysis?.follow_up_context;
  const matchedKeywords = readiness.matched_keywords || [];
  const missingSignals = readiness.missing_signals || [];
  const matchedSignals = readiness.matched_signals || [];

  const barClass =
    score >= 85 ? "high" : score >= 70 ? "good" : score >= 50 ? "fair" : "low";

  const hasSignalGrid = matchedSignals.length > 0 || missingSignals.length > 0;

  return (
    <div className={`${rootClass} workload-guidance--active animate-fade-in-up`}>
      <div className={`guidance-readiness readiness-status--${barClass}`}>
        <div className="guidance-header">
          <span className="guidance-title">{title}</span>
          <span className={`guidance-score guidance-score--${barClass}`} aria-label={`${score} percent ready`}>
            {score}%
          </span>
        </div>

        <div
          className="readiness-bar"
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Workload description readiness"
        >
          <div
            className={`readiness-bar-fill readiness-bar-fill--${barClass}`}
            style={{ width: `${Math.max(score, 4)}%` }}
          />
        </div>

        {readiness.readiness_label && (
          <p className="readiness-label">
            <span className="readiness-label-dot" aria-hidden="true" />
            {readiness.readiness_label}
          </p>
        )}
      </div>

      {analysis?.recommended_cluster && (
        <div className="guidance-preview">
          <span className="preview-cluster">
            Suggested: <strong>{analysis.recommended_cluster}</strong> cluster
          </span>
          <span className="preview-confidence">NLP confidence: {analysis.confidence}%</span>
          {analysis.auto_assign_eligible && (
            <span className="preview-badge">Ready for auto-assignment</span>
          )}
        </div>
      )}

      {hasSignalGrid && (
        <div className="guidance-signals-grid">
          {matchedSignals.length > 0 && (
            <div className="guidance-section guidance-section--detected">
              <span className="guidance-section-label">Detected</span>
              <div className="signal-chips signal-chips--matched">
                {matchedSignals.map((s) => (
                  <span key={s.id} className="signal-chip signal-chip--ok">
                    {s.label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {missingSignals.length > 0 && (
            <div className="guidance-section guidance-section--missing">
              <span className="guidance-section-label">Still helpful to add</span>
              <div className="signal-chips signal-chips--missing">
                {missingSignals.map((s) => (
                  <span key={s.id} className="signal-chip signal-chip--missing" title={s.hint}>
                    {s.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {matchedKeywords.length > 0 && (
        <div className="guidance-keywords">
          <span className="guidance-section-label">Keywords found</span>
          <div className="keyword-tags">
            {matchedKeywords.slice(0, 8).map((kw) => (
              <span key={kw} className="keyword-tag">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {questions.length > 0 && (
        <div className="guidance-questions">
          <span className="guidance-section-label">
            {followUpContext?.intro || "A few details to sharpen the recommendation"}
          </span>
          {followUpContext?.label && (
            <span className="guidance-context-tag">{followUpContext.label}</span>
          )}
          {questions.map((q) => (
            <div key={q.id} className="guidance-question form-group">
              <label htmlFor={`followup-${q.id}`}>{q.question}</label>
              <select
                id={`followup-${q.id}`}
                className="guidance-select"
                value={followUpAnswers[q.id] || ""}
                onChange={(e) => onFollowUpChange(q.id, e.target.value)}
              >
                <option value="">Choose an answer…</option>
                {q.options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
              {q.hint && <span className="follow-up-hint">{q.hint}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default WorkloadGuidancePanel;
