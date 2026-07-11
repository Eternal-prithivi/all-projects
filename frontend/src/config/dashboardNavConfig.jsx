import React from 'react';
import { IconDashboard, IconBarChart, IconHardDrive, IconServer, IconShield } from '../components/dashboard/Icons.jsx';
import { PATHS } from '../data/productFacts.js';

export const infrastructureIcon = (
  <svg className="rail-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path d="M5.5 16a3.5 3.5 0 01-.369-6.98 4 4 0 117.753-1.977A4.5 4.5 0 1113.5 16h-8z" />
    <path
      d="M10 9l3 3m0 0l-3 3m3-3H7"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    />
  </svg>
);

export const teamIcon = (
  <svg className="rail-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path d="M10 10a3 3 0 100-6 3 3 0 000 6zm-7 7a7 7 0 1114 0H3z" />
  </svg>
);

export const supportIcon = (
  <svg className="rail-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path
      fillRule="evenodd"
      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
      clipRule="evenodd"
    />
  </svg>
);

export const billingIcon = (
  <svg className="rail-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
    <path
      fillRule="evenodd"
      d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z"
      clipRule="evenodd"
    />
  </svg>
);

/** All dashboard destinations (desktop rail + more sheet). */
export const DASHBOARD_NAV_ITEMS = [
  { to: '/dashboard', icon: <IconDashboard className="rail-icon" />, label: 'Overview', end: true, navId: 'overview' },
  { to: '/dashboard/storage', icon: <IconHardDrive className="rail-icon" />, label: 'Storage', navId: 'storage' },
  { to: '/dashboard/vmcluster', icon: <IconServer className="rail-icon" />, label: 'VM Cluster', navId: 'vmcluster' },
  { to: '/dashboard/security', icon: <IconShield className="rail-icon" />, label: 'Security', navId: 'security' },
  {
    to: '/dashboard/provision',
    icon: infrastructureIcon,
    label: 'Infrastructure',
    navId: 'provision',
    navLockId: 'provision_policies',
    lockNavBlock: false,
  },
  { to: '/dashboard/costs', icon: <IconBarChart className="rail-icon" />, label: 'Cost Analysis', navId: 'costs' },
  {
    to: '/dashboard/team',
    icon: teamIcon,
    label: 'Team',
    navId: 'team',
    navLockId: 'team_seat_billing',
    lockNavBlock: false,
  },
  { to: '/dashboard/billing', icon: billingIcon, label: 'Billing', navId: 'billing' },
  { to: PATHS.help, icon: supportIcon, label: 'Help & Support', navId: 'support', isHelp: true },
];

/** Cost hub sub-routes (Pro+ tools). */
export const COST_HUB_LINKS = [
  { to: '/dashboard/costs', label: 'Analysis', end: true, navId: 'costs' },
  { to: '/dashboard/simulator', label: 'Simulator', navId: 'cost_simulator', lockNavBlock: true },
  { to: '/dashboard/optimization', label: 'Optimization', navId: 'cost_optimization', lockNavBlock: true },
  { to: '/dashboard/pricing', label: 'Pricing', navId: 'billing' },
];

/** Primary bottom tabs on mobile (max 5). */
export const DASHBOARD_MOBILE_PRIMARY = [
  DASHBOARD_NAV_ITEMS[0],
  DASHBOARD_NAV_ITEMS[1],
  DASHBOARD_NAV_ITEMS[4],
  DASHBOARD_NAV_ITEMS[5],
];

/** Shown in mobile "More" sheet. */
export function getDashboardMobileMoreItems(user) {
  const more = [
    DASHBOARD_NAV_ITEMS[2],
    DASHBOARD_NAV_ITEMS[3],
    { to: '/dashboard/simulator', label: 'Cost simulator', navId: 'cost_simulator', lockNavBlock: true },
    { to: '/dashboard/optimization', label: 'Cost optimization', navId: 'cost_optimization', lockNavBlock: true },
    DASHBOARD_NAV_ITEMS[6],
    DASHBOARD_NAV_ITEMS[7],
    { to: PATHS.help, label: 'Help & Support', external: false, isHelp: true },
    { to: '/dashboard/settings', label: 'Settings', isSettings: true },
  ];
  if (user?.role === 'admin') {
    more.unshift({ to: '/admin', label: 'Admin Portal', isAdmin: true });
  }
  return more;
}
