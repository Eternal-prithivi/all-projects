import React from 'react';
import { Link } from 'react-router-dom';
import { FaLock } from 'react-icons/fa';
import { PATHS } from '../../data/productFacts.js';
import { MIN_PLAN_LABELS } from '../../config/planNavConfig.js';
import '../../styles/plan-upgrade.css';

export default function PlanUpgradeGate({
  featureLabel = 'This feature',
  currentPlan = 'Free',
  requiredPlan = 'Pro',
  requiredPlanId = 'pro',
  compact = false,
}) {
  const requiredName = MIN_PLAN_LABELS[requiredPlanId] || requiredPlan;

  return (
    <div className={`plan-upgrade-gate ${compact ? 'plan-upgrade-gate--compact' : ''}`}>
      <div className="plan-upgrade-gate__icon" aria-hidden="true">
        <FaLock />
      </div>
      <h3>{featureLabel}</h3>
      <p>
        Your <strong>{currentPlan}</strong> plan does not include this capability.
        Upgrade to <strong>{requiredName}</strong> or above to unlock it.
      </p>
      <Link to={PATHS.pricing} className="plan-upgrade-gate__cta">
        View plans &amp; upgrade
      </Link>
    </div>
  );
}
