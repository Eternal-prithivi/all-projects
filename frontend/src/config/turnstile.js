/** Cloudflare Turnstile site key for login/register CAPTCHA. */
export const turnstileSiteKey = () =>
  (import.meta.env.VITE_TURNSTILE_SITE_KEY || '').trim();
