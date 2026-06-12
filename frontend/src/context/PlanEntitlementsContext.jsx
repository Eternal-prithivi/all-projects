import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { usePlanEntitlements } from '../hooks/usePlanEntitlements.js';
import PlanUpgradeDrawer from '../components/billing/PlanUpgradeDrawer.jsx';
import { NAV_ID_LABELS, MIN_PLAN_LABELS } from '../config/planNavConfig.js';

const PlanEntitlementsContext = createContext(null);

export function PlanEntitlementsProvider({ children }) {
  const ent = usePlanEntitlements();
  const [drawer, setDrawer] = useState(null);

  const openUpgradeDrawer = useCallback((navId) => {
    const meta = ent.getNavMeta(navId);
    setDrawer({
      navId,
      label: NAV_ID_LABELS[navId] || navId,
      minPlan: meta?.min_plan || 'pro',
      minPlanName: MIN_PLAN_LABELS[meta?.min_plan] || 'Pro',
      currentPlan: ent.planName,
    });
  }, [ent]);

  const closeUpgradeDrawer = useCallback(() => setDrawer(null), []);

  const value = useMemo(
    () => ({
      ...ent,
      openUpgradeDrawer,
      closeUpgradeDrawer,
    }),
    [ent, openUpgradeDrawer, closeUpgradeDrawer]
  );

  return (
    <PlanEntitlementsContext.Provider value={value}>
      {children}
      <PlanUpgradeDrawer
        open={Boolean(drawer)}
        onClose={closeUpgradeDrawer}
        featureLabel={drawer?.label}
        currentPlan={drawer?.currentPlan}
        requiredPlan={drawer?.minPlanName}
        requiredPlanId={drawer?.minPlan}
      />
    </PlanEntitlementsContext.Provider>
  );
}

export function usePlanEntitlementsContext() {
  const ctx = useContext(PlanEntitlementsContext);
  if (!ctx) {
    throw new Error('usePlanEntitlementsContext must be used within PlanEntitlementsProvider');
  }
  return ctx;
}
