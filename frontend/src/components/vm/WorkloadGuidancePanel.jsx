import React from "react";

/**
 * Live NLP readiness bar, missing signals, follow-up Q&A, and cluster preview.
 */
function WorkloadGuidancePanel({
  analysis,
  isAnalyzing,
  followUpAnswers,
  onFollowUpChange,
}) {
  if (!analysis && !isAnalyzing) {
    return (
      <div className="workload-guidance workload-guidance--idle">
        <p className="guidance-hint">
          Describe your workload above — we&apos;ll show how complete your prompt is
          and suggest a cluster before you request a VM.
        </p>
      </div>
    );
  }

  if (isAnalyzing && !analysis) {
    return (
      <div className="workload-guidance workload-guidance--loading">
        <p className="guidance-hint">Analyzing workload…</p>
      </div>
    );
  }

  const readiness = analysis?.readiness || {};
  const score = readiness.readiness_score ?? 0;
  const questions = analysis?.follow_up_questions || [];
  const matchedKeywords = readiness.matched_keywords || [];
  const missingSignals = readiness.missing_signals || [];
  const matchedSignals = readiness.matched_signals || [];

  const barClass =
    score >= 85 ? "high" : score >= 70 ? "good" : score >= 50 ? "fair" : "low";

  return (
    <div className="workload-guidance workload-guidance--active animate-fade-in-up">
      <div className="guidance-header">
        <span className="guidance-title">Prompt readiness for NLP</span>
        <span className={`guidance-score guidance-score--${barClass}`}>{score}%</span>
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
          style={{ width: `${score}%` }}
        />
      </div>
      <p className="readiness-label">{readiness.readiness_label}</p>

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

      {matchedSignals.length > 0 && (
        <div className="guidance-section">
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
        <div className="guidance-section">
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
          <span className="guidance-section-label">Quick questions (improves accuracy)</span>
          {questions.map((q) => (
            <div key={q.id} className="form-group">
              <label htmlFor={`followup-${q.id}`}>{q.question}</label>
              <select
                id={`followup-${q.id}`}
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
