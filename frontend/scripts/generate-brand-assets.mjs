#!/usr/bin/env node
/** Regenerate public/ favicons and og-image from ../Logos/zenith-icon.png */
import sharp from 'sharp';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const BRAND_BG = '#050505';

const frontendRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const publicRoot = path.join(frontendRoot, 'public');
const sourceLogo = path.join(frontendRoot, '..', 'Logos', 'zenith-icon.png');

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

/** Favicon / PWA: matte pad + optical center (mark sits slightly lower in box). */
const padIcon = async (size, bg = BRAND_BG) => {
  const padTop = Math.round(size * 0.09);
  const padBottom = Math.round(size * 0.04);
  const padSide = Math.round(size * 0.06);
  return transparentPng
    .clone()
    .resize(size - padTop - padBottom, size - padSide * 2, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .extend({
      top: padTop,
      bottom: padBottom,
      left: padSide,
      right: padSide,
      background: bg,
    })
    .png()
    .toBuffer();
};

const icon512 = await padIcon(512);
const icon192 = await padIcon(192);
const icon48 = await padIcon(48);

await sharp(icon512).toFile(path.join(publicRoot, 'icon-512.png'));
await sharp(icon192).toFile(path.join(publicRoot, 'icon-192.png'));
await sharp(icon48).toFile(path.join(publicRoot, 'favicon-48.png'));
await sharp(icon192).toFile(path.join(publicRoot, 'favicon.ico'));

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

console.log('Brand assets generated → frontend/public/ (UI transparent + SEO on #050505)');
