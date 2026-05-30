import { describe, expect, it } from 'vitest';
import {
  getEngineLabel,
  getProvisionEngine,
  getRemediateConfirmMessage,
} from './provisionEngine.js';

describe('provisionEngine', () => {
  it('detects boto3 from provision_engine', () => {
    expect(getProvisionEngine({ provision_engine: 'boto3' })).toBe('boto3');
  });

  it('detects boto3 from fast_path legacy', () => {
    expect(getProvisionEngine({ fast_path: true })).toBe('boto3');
  });

  it('remediate confirm mentions Boto3', () => {
    expect(getRemediateConfirmMessage('boto3')).toMatch(/Boto3/i);
    expect(getRemediateConfirmMessage('terraform')).toMatch(/Terraform/i);
  });

  it('labels engines', () => {
    expect(getEngineLabel('boto3')).toBe('Boto3');
    expect(getEngineLabel('terraform')).toBe('Terraform');
  });
});
