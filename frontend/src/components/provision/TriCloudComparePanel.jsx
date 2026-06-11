import React from "react";

export default function TriCloudComparePanel({
  comparisons,
  loading,
  selectedCsp,
  onSelect,
  templates,
  selectedTemplate,
  onSelectTemplate,
}) {
  if (loading) {
    return (
      <div className="provision-loading">
        <div className="provision-spinner" />
        <span>Comparing clouds…</span>
      </div>
    );
  }

  return (
    <div className="tri-cloud-compare">
      <div className="section-header">
        <h3>Pick your cloud &amp; template</h3>
        <p>Compare estimated monthly cost and fit across providers, then choose one.</p>
      </div>

      <div className="template-grid">
        {templates.map((tmpl) => (
          <div
            key={tmpl.key}
            className={`template-card ${selectedTemplate === tmpl.key ? "selected" : ""}`}
            onClick={() => onSelectTemplate(tmpl)}
            onKeyDown={(e) => e.key === "Enter" && onSelectTemplate(tmpl)}
            role="button"
            tabIndex={0}
          >
            <h3>{tmpl.name}</h3>
            <p>{tmpl.description}</p>
          </div>
        ))}
      </div>

      {comparisons.length > 0 && (
        <div className="compare-grid">
          {comparisons.map((row) => (
            <button
              key={row.csp}
              type="button"
              className={`compare-card ${selectedCsp === row.csp ? "selected" : ""}`}
              onClick={() => onSelect(row)}
            >
              {row.badge === "best_fit" && <span className="compare-badge">Best fit</span>}
              {row.badge === "best_value" && <span className="compare-badge value">Best value</span>}
              <h4>{row.csp}</h4>
              <p className="compare-cost">${row.monthly_cost}/mo</p>
              <p className="compare-fit">Fit score: {row.fit_score}</p>
              <p className="compare-instance">{row.recommended_instance}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
