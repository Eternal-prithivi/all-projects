import React from 'react';
import { IconDashboard, IconBarChart, IconHardDrive, IconServer, IconShield } from '../components/dashboard/Icons.jsx';

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
  { to: '/dashboard', icon: <IconDashboard className="rail-icon" />, label: 'Overview', end: true },
  { to: '/dashboard/storage', icon: <IconHardDrive className="rail-icon" />, label: 'Storage' },
  { to: '/dashboard/vmcluster', icon: <IconServer className="rail-icon" />, label: 'VM Cluster' },
  { to: '/dashboard/security', icon: <IconShield className="rail-icon" />, label: 'Security' },
  { to: '/dashboard/provision', icon: infrastructureIcon, label: 'Infrastructure' },
  { to: '/dashboard/costs', icon: <IconBarChart className="rail-icon" />, label: 'Cost Analysis' },
  { to: '/dashboard/team', icon: teamIcon, label: 'Team' },
  { to: '/dashboard/billing', icon: billingIcon, label: 'Billing' },
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
    DASHBOARD_NAV_ITEMS[6],
    DASHBOARD_NAV_ITEMS[7],
    { to: '/help', label: 'Help Center', external: false, isHelp: true },
    { to: '/dashboard/settings', label: 'Settings', isSettings: true },
  ];
  if (user?.role === 'admin') {
    more.unshift({ to: '/admin', label: 'Admin Portal', isAdmin: true });
  }
  return more;
}
