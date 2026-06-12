import React from 'react';
import { usePlanEntitlementsContext } from '../../context/PlanEntitlementsContext.jsx';
import PlanUpgradeGate from './PlanUpgradeGate.jsx';
import { NAV_ID_LABELS, MIN_PLAN_LABELS } from '../../config/planNavConfig.js';

export default function PlanFeatureRoute({ navId, children }) {
  const { isNavLocked, getNavMeta, planName, loading } = usePlanEntitlementsContext();

  if (loading) {
    return null;
  }

  if (isNavLocked(navId)) {
    const meta = getNavMeta(navId);
    return (
      <PlanUpgradeGate
        featureLabel={NAV_ID_LABELS[navId] || navId}
        currentPlan={planName}
        requiredPlan={MIN_PLAN_LABELS[meta?.min_plan] || 'Pro'}
        requiredPlanId={meta?.min_plan || 'pro'}
      />
    );
  }

  return children;
}
