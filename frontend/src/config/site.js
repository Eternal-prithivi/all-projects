/** Public site URL for SEO, Open Graph, and sitemap (set VITE_SITE_URL in Vercel). */
export const SITE_URL = (
  import.meta.env.VITE_SITE_URL || 'https://zenith-frontend.vercel.app'
).replace(/\/$/, '');

export const SITE_NAME = 'Zenith Cloud Platform';
export const SITE_TITLE = 'Zenith Cloud Platform';
export const SITE_DESCRIPTION =
  'Zenith is a multi-cloud resource optimization platform for AWS, GCP, and Azure — cost analytics, smart storage tiering, VM clusters, and secure infrastructure provisioning.';

export const OG_IMAGE_PATH = '/og-image.png';
export const LOGO_ICON_PATH = '/zenith-icon.svg';
export const LOGO_WORDMARK_PATH = '/zenith-logo.svg';
