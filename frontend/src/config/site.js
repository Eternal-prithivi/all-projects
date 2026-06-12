/** Public site URL for SEO, Open Graph, and sitemap (set VITE_SITE_URL in Vercel). */
export const SITE_URL = (
  import.meta.env.VITE_SITE_URL || 'https://rajverse.me'
).replace(/\/$/, '');

export const SITE_NAME = 'Zenith Cloud Platform';
export const SITE_TITLE = 'Zenith Cloud Platform';
export const SITE_DESCRIPTION =
  'Zenith is a multi-cloud resource optimization platform for AWS, GCP, and Azure — cost analytics, smart storage tiering, VM clusters, and secure infrastructure provisioning.';

export const OG_IMAGE_PATH = '/og-image.png';

/**
 * Bump when regenerating public/ favicons (npm run brand:assets) so browsers
 * and Google Search drop cached old marks.
 */
export const BRAND_ASSET_VERSION = '5';

/** Served from public/; source master is assets/brand/zenith-icon.png */
export const LOGO_ICON_PATH = `/zenith-icon.png?v=${BRAND_ASSET_VERSION}`;

export const faviconHref = (file) => `/${file}?v=${BRAND_ASSET_VERSION}`;
