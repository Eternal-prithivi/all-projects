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
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react-dom') || id.includes('react-router')) {
              return 'vendor-react';
            }
            if (id.includes('recharts')) {
              return 'vendor-charts';
            }
            if (id.includes('react-joyride') || id.includes('react-floater')) {
              return 'vendor-joyride';
            }
            if (id.includes('jspdf')) {
              return 'vendor-pdf';
            }
            if (id.includes('react-icons')) {
              return 'vendor-icons';
            }
          }
        },
      },
    },
  },
});
