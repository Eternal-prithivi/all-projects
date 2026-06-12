/** Maps dashboard routes and sections to entitlement nav IDs. */

export const ROUTE_NAV_ENTITLEMENTS = {
  '/dashboard/optimization': 'cost_optimization',
  '/dashboard/simulator': 'cost_simulator',
};

export const NAV_ID_LABELS = {
  provision_policies: 'Provision policies',
  cost_optimization: 'Cost optimization',
  cost_simulator: 'Cost simulator',
  team_seat_billing: 'Team seat billing',
  byoc: 'Bring your own cloud',
  api_access: 'API access',
};

export const MIN_PLAN_LABELS = {
  basic: 'Basic',
  pro: 'Pro',
  enterprise: 'Enterprise',
};
