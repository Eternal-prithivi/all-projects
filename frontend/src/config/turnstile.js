/** Cloudflare Turnstile site key for register-page CAPTCHA. */
export const turnstileSiteKey = () =>
  (import.meta.env.VITE_TURNSTILE_SITE_KEY || '').trim();
