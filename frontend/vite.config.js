import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const SITE_URL = (process.env.VITE_SITE_URL || 'https://rajverse.me').replace(/\/$/, '');

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'inject-site-url',
      transformIndexHtml(html) {
        return html.replace(/https:\/\/rajverse\.me/g, SITE_URL);
      },
    },
  ],
});
