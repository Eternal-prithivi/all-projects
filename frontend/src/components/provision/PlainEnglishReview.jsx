import React from "react";

export default function PlainEnglishReview({ summary, loading }) {
  if (loading) {
    return (
      <div className="provision-loading">
        <div className="provision-spinner" />
        <span>Preparing summary…</span>
      </div>
    );
  }
  if (!summary) return null;

  return (
    <div className="plain-english-review">
      <h3>What we will create</h3>
      <ul className="plain-english-bullets">
        {(summary.plain_english_bullets || []).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      {(summary.warnings || []).length > 0 && (
        <div className="plain-english-warnings">
          {(summary.warnings || []).map((w) => (
            <p key={w}>⚠️ {w}</p>
          ))}
        </div>
      )}
    </div>
  );
}
