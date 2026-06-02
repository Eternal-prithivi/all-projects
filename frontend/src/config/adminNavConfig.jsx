import React from 'react';
import { FaChartLine, FaUsers, FaDollarSign, FaServer, FaHome, FaQuestionCircle } from 'react-icons/fa';

export const ADMIN_NAV_ITEMS = [
  { to: '/admin', icon: <FaChartLine className="rail-icon" />, label: 'Overview', end: true },
  { to: '/admin/users', icon: <FaUsers className="rail-icon" />, label: 'Users' },
  { to: '/admin/analytics', icon: <FaChartLine className="rail-icon" />, label: 'Analytics' },
  { to: '/admin/payments', icon: <FaDollarSign className="rail-icon" />, label: 'Payments' },
  { to: '/admin/system', icon: <FaServer className="rail-icon" />, label: 'System' },
];

export const ADMIN_MOBILE_PRIMARY = [
  ADMIN_NAV_ITEMS[0],
  ADMIN_NAV_ITEMS[1],
  ADMIN_NAV_ITEMS[3],
];

export function getAdminMobileMoreItems(user) {
  const initial = user?.username?.charAt(0).toUpperCase() || 'A';
  return [
    ADMIN_NAV_ITEMS[2],
    ADMIN_NAV_ITEMS[4],
    { to: '/dashboard', icon: <FaHome className="rail-icon" />, label: 'Dashboard' },
    { to: '/admin/settings', label: 'Admin Settings', isSettings: true, userInitial: initial },
    { to: '/help', icon: <FaQuestionCircle className="rail-icon" />, label: 'Help Center' },
  ];
}
