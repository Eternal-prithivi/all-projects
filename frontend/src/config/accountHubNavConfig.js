import { PATHS } from '../data/productFacts.js';

/** Shared sub-nav for Profile, Security, and Workspace Settings. */
export const ACCOUNT_HUB_LINKS = [
  { to: PATHS.profile, label: 'Profile', end: true },
  { to: PATHS.securitySettings, label: 'Security' },
  { to: PATHS.settings, label: 'Workspace settings' },
];
