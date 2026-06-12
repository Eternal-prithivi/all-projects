import { describe, expect, it } from 'vitest';
import {
  getEffectiveEngineLabel,
  getEngineLabel,
  getProvisionEngine,
  getRemediateConfirmMessage,
} from './provisionEngine.js';

describe('provisionEngine', () => {
  it('detects boto3 from provision_engine', () => {
    expect(getProvisionEngine({ provision_engine: 'boto3' })).toBe('boto3');
  });

  it('detects sdk from fast_path on GCP', () => {
    expect(getProvisionEngine({ fast_path: true, config: { csp: 'GCP' } })).toBe('sdk');
  });

  it('detects boto3 from fast_path legacy on AWS', () => {
    expect(getProvisionEngine({ fast_path: true, config: { csp: 'AWS' } })).toBe('boto3');
  });

  it('remediate confirm is cloud-aware for fast path', () => {
    expect(getRemediateConfirmMessage('boto3', 'AWS')).toMatch(/AWS SDK/i);
    expect(getRemediateConfirmMessage('sdk', 'GCP')).toMatch(/Google Cloud SDK/i);
    expect(getRemediateConfirmMessage('terraform')).toMatch(/Terraform/i);
  });

  it('labels engines per cloud when known', () => {
    expect(getEngineLabel('boto3', 'AWS')).toMatch(/Boto3/i);
    expect(getEngineLabel('sdk', 'GCP')).toBe('Google Cloud SDK');
    expect(getEngineLabel('terraform')).toBe('Terraform');
  });

  it('uses generic Cloud SDK for preference toggle', () => {
    expect(getEffectiveEngineLabel('boto3')).toBe('Cloud SDK');
    expect(getEffectiveEngineLabel('terraform')).toBe('Terraform');
  });
});
