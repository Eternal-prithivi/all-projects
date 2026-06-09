import React from 'react';

const EXPERT_LABELS = {
  rule: 'Rule engine',
  random_forest: 'Random Forest',
  xgboost: 'XGBoost',
};

const TIER_LABELS = {
  hot: 'Hot',
  warm: 'Warm',
  cold: 'Cold',
};

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${Math.round(Number(value) * 100)}%`;
}

function formatWeight(value) {
  if (value == null || Number.isNaN(Number(value))) return '';
  return `${Math.round(Number(value) * 100)}% weight`;
}

function formatFeatureName(name) {
  return String(name || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const FILE_TYPE_BY_CODE = {
  0: 'archive',
  1: 'data',
  2: 'media',
  3: 'document',
};

function decodePriority(features) {
  if (features.priority_cost) return 'cost';
  if (features.priority_performance) return 'performance';
  return 'balanced';
}

function decodeIntent(features) {
  if (features.intent_archival) return 'archival';
  if (features.intent_infrequent) return 'infrequent';
  if (features.intent_frequent) return 'frequent';
  return 'active';
}

export default function StorageEnsembleBreakdown({ recommendation }) {
  if (!recommendation) return null;

  const votes = recommendation.expert_votes || [];
  const tierScores = recommendation.tier_scores || {};
  const shap = recommendation.shap_explanation;
  const modelStatus = recommendation.model_status;
  const isEnsemble = modelStatus?.mode === 'ensemble';
  const finalTier = recommendation.determined_tier;
  const maxTierScore = Math.max(...Object.values(tierScores).map(Number), 0.0001);

  const whyParts = [];
  if (shap?.summary) {
    whyParts.push(shap.summary);
  }
  const features = recommendation.input_features || {};
  if (recommendation.recommendation?.csp) {
    whyParts.push(
      `${recommendation.recommendation.csp} was selected for the ${TIER_LABELS[finalTier] || finalTier} tier ` +
        `based on storage cost, retrieval penalty, and your ${decodePriority(features)} priority.`,
    );
  }
  if (!isEnsemble && modelStatus?.error) {
    whyParts.push(
      `ML models were unavailable (${modelStatus.error}). The rule engine result was used.`,
    );
  } else if (isEnsemble) {
    whyParts.push(
      'Zenith combines a rule engine (30%), Random Forest (35%), and XGBoost (35%) into one weighted vote across hot, warm, and cold tiers.',
    );
  }

  return (
    <div className="ensemble-box ensemble-box--compact storage-ensemble-breakdown">
      <div className="ensemble-summary">
        <span>Ensemble result</span>
        <strong>
          {TIER_LABELS[finalTier] || finalTier} · {formatPercent(recommendation.ensemble_confidence)}
        </strong>
      </div>

      <p className="storage-ensemble-breakdown__lead">
        Each expert predicts a workload tier. Scores below are per-model confidence; the final tier
        is a weighted vote across all experts.
      </p>

      <div className="expert-votes expert-votes--compact">
        {votes.map((vote) => {
          const isWinner = vote.predicted_tier === finalTier;
          return (
            <div
              key={vote.expert}
              className={`expert-vote${isWinner ? ' expert-vote--winner' : ''}`}
            >
              <span>{EXPERT_LABELS[vote.expert] || vote.expert}</span>
              <strong>{TIER_LABELS[vote.predicted_tier] || vote.predicted_tier}</strong>
              <small>{formatPercent(vote.confidence)} confidence</small>
              <small>{formatWeight(vote.weight)}</small>
            </div>
          );
        })}
      </div>

      {Object.keys(tierScores).length > 0 && (
        <div className="tier-scores">
          <p className="tier-scores__title">Weighted tier scores</p>
          {['hot', 'warm', 'cold'].map((tier) => {
            const score = Number(tierScores[tier] || 0);
            const width = Math.max(4, (score / maxTierScore) * 100);
            const isWinner = tier === finalTier;
            return (
              <div key={tier} className={`tier-score-row${isWinner ? ' tier-score-row--winner' : ''}`}>
                <span className="tier-score-row__label">{TIER_LABELS[tier]}</span>
                <div className="tier-score-row__track" aria-hidden>
                  <div className="tier-score-row__fill" style={{ width: `${width}%` }} />
                </div>
                <span className="tier-score-row__value">{score.toFixed(3)}</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="shap-box storage-ensemble-breakdown__why">
        <p className="storage-ensemble-breakdown__why-title">Why this recommendation</p>
        {whyParts.map((text) => (
          <p key={text} className="shap-summary">
            {text}
          </p>
        ))}
        {shap?.top_features?.length > 0 && (
          <ul className="shap-features">
            {shap.top_features.slice(0, 4).map((row) => (
              <li key={row.feature}>
                <span>{formatFeatureName(row.feature)}</span>
                <span>{row.impact != null ? Number(row.impact).toFixed(3) : row.value}</span>
              </li>
            ))}
          </ul>
        )}
        {Object.keys(features).length > 0 && (
          <p className="rl-policy-note">
            Inputs: {FILE_TYPE_BY_CODE[features.file_type_code] || 'document'} file ·{' '}
            {Number(features.file_size_mb || 0).toFixed(2)} MB · intent {decodeIntent(features)} ·
            priority {decodePriority(features)}
            {recommendation.analysis_score != null && ` · rule score ${recommendation.analysis_score}`}
          </p>
        )}
      </div>
    </div>
  );
}
