#!/usr/bin/env node
/**
 * Regenerate PNG favicons and OG image from SVG sources.
 * Requires: npm install sharp (dev)
 */
import sharp from 'sharp';
import { fileURLToPath } from 'url';
import path from 'path';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public');

await Promise.all([
  sharp(path.join(root, 'zenith-icon.svg')).resize(192, 192).png().toFile(path.join(root, 'icon-192.png')),
  sharp(path.join(root, 'zenith-icon.svg')).resize(512, 512).png().toFile(path.join(root, 'icon-512.png')),
  sharp(path.join(root, 'og-image.svg')).resize(1200, 630).png().toFile(path.join(root, 'og-image.png')),
  sharp(path.join(root, 'icon.svg')).resize(48, 48).png().toFile(path.join(root, 'favicon-48.png')),
]);

await sharp(path.join(root, 'icon-192.png')).toFile(path.join(root, 'favicon.ico'));

console.log('Brand PNG assets written to frontend/public/');
