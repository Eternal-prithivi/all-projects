import { BRAND_ASSET_VERSION } from './site.js';

const asset = (file) => `/images/${file}?v=${BRAND_ASSET_VERSION}`;

/** Canonical cloud provider logo paths (AWS uses dark-background mark). */
export const CLOUD_PROVIDER_LOGOS = {
  AWS: asset('aws.png'),
  GCP: asset('google-cloud_logo.png'),
  Azure: asset('Microsoft_Azure.png'),
};

const LOWER_MAP = {
  aws: CLOUD_PROVIDER_LOGOS.AWS,
  gcp: CLOUD_PROVIDER_LOGOS.GCP,
  azure: CLOUD_PROVIDER_LOGOS.Azure,
};

/** Resolve logo URL from AWS | GCP | Azure or aws | gcp | azure. */
export function getCloudProviderLogo(provider) {
  if (!provider) return null;
  const key = String(provider).trim();
  if (CLOUD_PROVIDER_LOGOS[key]) return CLOUD_PROVIDER_LOGOS[key];
  const upper = key.toUpperCase();
  if (upper === 'AWS') return CLOUD_PROVIDER_LOGOS.AWS;
  if (upper === 'GCP') return CLOUD_PROVIDER_LOGOS.GCP;
  if (upper === 'AZURE') return CLOUD_PROVIDER_LOGOS.Azure;
  return LOWER_MAP[key.toLowerCase()] || null;
}
