import React from 'react';
import { getCloudProviderLogo } from '../../config/cloudProviderLogos.js';

const PROVIDER_LABELS = {
  AWS: 'Amazon Web Services',
  GCP: 'Google Cloud',
  Azure: 'Microsoft Azure',
};

function labelFor(provider) {
  const key = String(provider || '').trim().toUpperCase();
  if (key === 'AWS') return PROVIDER_LABELS.AWS;
  if (key === 'GCP') return PROVIDER_LABELS.GCP;
  if (key === 'AZURE') return PROVIDER_LABELS.Azure;
  return String(provider || '');
}

export default function CloudProviderLogo({
  provider,
  className = '',
  width,
  height,
  alt,
  title,
  ...imgProps
}) {
  const src = getCloudProviderLogo(provider);
  if (!src) return null;

  const resolvedAlt = alt === '' ? '' : (alt ?? labelFor(provider));

  return (
    <img
      src={src}
      alt={resolvedAlt}
      className={className}
      width={width}
      height={height}
      title={title ?? (resolvedAlt || undefined)}
      {...imgProps}
    />
  );
}
