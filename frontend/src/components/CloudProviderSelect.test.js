import { describe, expect, it } from 'vitest';
import { filterFilesByCloudProvider } from './CloudProviderSelect.jsx';

describe('filterFilesByCloudProvider', () => {
  const files = [
    { filename: 'a.txt', csp: 'AWS' },
    { filename: 'b.txt', csp: 'GCP' },
    { filename: 'c.txt' },
  ];

  it('returns all files when provider is ALL', () => {
    expect(filterFilesByCloudProvider(files, 'ALL')).toHaveLength(3);
  });

  it('filters by provider', () => {
    expect(filterFilesByCloudProvider(files, 'GCP')).toHaveLength(1);
    expect(filterFilesByCloudProvider(files, 'AWS')).toHaveLength(2);
  });
});
