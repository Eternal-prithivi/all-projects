#!/usr/bin/env node
/** Regenerate public/ favicons and og-image from ../assets/brand/zenith-icon.png */
import sharp from 'sharp';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const BRAND_BG = '#050505';

const frontendRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const publicRoot = path.join(frontendRoot, 'public');
const sourceLogo = path.join(frontendRoot, '..', 'assets', 'brand', 'zenith-icon.png');

if (!fs.existsSync(sourceLogo)) {
  console.error('Missing source logo:', sourceLogo);
  process.exit(1);
}

/** Turn near-black matte into alpha so the mark sits on any page background. */
async function logoWithTransparentBg(input, { threshold = 42, feather = 58 } = {}) {
  const { data, info } = await sharp(input)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const max = Math.max(r, g, b);
    if (max <= threshold) {
      data[i + 3] = 0;
    } else if (max <= feather) {
      const t = (max - threshold) / (feather - threshold);
      data[i + 3] = Math.round(Math.min(255, t * 255));
    }
  }

  return sharp(data, {
    raw: { width: info.width, height: info.height, channels: 4 },
  }).png();
}

const transparentPng = await logoWithTransparentBg(sourceLogo);

/** UI + schema: square transparent PNG (Google Organization logo). */
await transparentPng
  .clone()
  .resize(512, 512, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toFile(path.join(publicRoot, 'zenith-icon.png'));

/**
 * Favicon / PWA: matte pad — scale mark larger on small sizes so the full "Z" reads
 * (avoids looking like a lone gold triangle in browser / Google search UI).
 */
const padIcon = async (size, bg = BRAND_BG) => {
  const padRatio = size <= 48 ? 0.06 : size <= 96 ? 0.07 : 0.08;
  const pad = Math.max(2, Math.round(size * padRatio));
  const inner = size - pad * 2;
  return transparentPng
    .clone()
    .resize(inner, inner, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .extend({
      top: pad,
      bottom: pad,
      left: pad,
      right: pad,
      background: bg,
    })
    .png()
    .toBuffer();
};

const sizes = [16, 32, 48, 96, 192, 512];
const icons = {};
for (const size of sizes) {
  icons[size] = await padIcon(size);
}

await sharp(icons[512]).toFile(path.join(publicRoot, 'icon-512.png'));
await sharp(icons[192]).toFile(path.join(publicRoot, 'icon-192.png'));
await sharp(icons[96]).toFile(path.join(publicRoot, 'favicon-96.png'));
await sharp(icons[48]).toFile(path.join(publicRoot, 'favicon-48.png'));
await sharp(icons[32]).toFile(path.join(publicRoot, 'favicon-32.png'));
await sharp(icons[16]).toFile(path.join(publicRoot, 'favicon-16.png'));
/** Root favicon — 48px PNG (widely used by Google Search + browsers). */
await sharp(icons[48]).toFile(path.join(publicRoot, 'favicon.ico'));

const ogMarkSize = 300;
const ogLogo = await transparentPng
  .clone()
  .resize(ogMarkSize, ogMarkSize, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toBuffer();

const ogTextSvg = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <rect width="1200" height="630" fill="${BRAND_BG}"/>
  <text x="600" y="400" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="72" font-weight="700" fill="#faf8f4">Zenith</text>
  <text x="600" y="458" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="600" letter-spacing="0.22em" fill="#d4af37">CLOUD PLATFORM</text>
</svg>`);

const ogMarkTop = 118;
const ogMarkLeft = Math.round((1200 - ogMarkSize) / 2);

await sharp(ogTextSvg)
  .composite([{ input: ogLogo, left: ogMarkLeft, top: ogMarkTop }])
  .png()
  .toFile(path.join(publicRoot, 'og-image.png'));

const BRAND_VERSION = '3';
fs.writeFileSync(
  path.join(publicRoot, 'brand-asset-version.txt'),
  BRAND_VERSION,
  'utf8',
);

console.log(`Brand assets generated → frontend/public/ (v${BRAND_VERSION})`);
