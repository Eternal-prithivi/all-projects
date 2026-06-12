import React from 'react';

/**
 * Direct module selection — for users who already know the service (S3, GCS, Blob, etc.).
 */
export default function ProvisionCatalogPicker({
  modules,
  config,
  csp,
  loading = false,
  availableProviders = [],
  onCspChange,
  onToggleModule,
}) {
  const providers = availableProviders.length > 0 ? availableProviders : [csp];

  return (
    <div className="provision-catalog-picker">
      <div className="provision-catalog-cloud">
        <span className="provision-catalog-cloud__label">Cloud provider</span>
        {providers.length > 1 ? (
          <div className="provision-catalog-cloud__options" role="radiogroup" aria-label="Cloud provider">
            {providers.map((provider) => (
              <button
                key={provider}
                type="button"
                role="radio"
                aria-checked={csp === provider}
                className={`provision-catalog-cloud__btn ${csp === provider ? 'active' : ''}`}
                onClick={() => onCspChange?.(provider)}
              >
                {provider}
              </button>
            ))}
          </div>
        ) : (
          <span className="provision-catalog-cloud__single">
            <strong>{csp}</strong>
          </span>
        )}
      </div>

      <p className="provision-catalog-picker__lead">
        Pick the services you want on <strong>{csp}</strong>. Enable several modules and configure
        them on the next steps — no description required.
      </p>

      {loading ? (
        <p className="provision-catalog-empty">Loading modules for {csp}…</p>
      ) : !modules?.length ? (
        <p className="provision-catalog-empty">No modules available for {csp}.</p>
      ) : (
        <div className="provision-catalog-grid">
          {modules.map((mod) => (
            <button
              key={mod.key}
              type="button"
              className={`provision-catalog-card ${config[mod.flag] ? 'selected' : ''}`}
              onClick={() => onToggleModule(mod.flag)}
              aria-pressed={Boolean(config[mod.flag])}
            >
              <span className="provision-catalog-card__name">{mod.name}</span>
              <span className="provision-catalog-card__desc">{mod.desc || mod.description}</span>
              {config[mod.flag] && <span className="provision-catalog-card__badge">Selected</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
