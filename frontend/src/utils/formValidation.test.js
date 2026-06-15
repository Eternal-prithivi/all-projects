import { describe, expect, it } from 'vitest';
import {
  isValidEmail,
  validateLoginForm,
  validateRegisterForm,
  validateByocAwsStep1,
} from './formValidation.js';

describe('formValidation', () => {
  it('validates email addresses', () => {
    expect(isValidEmail('user@example.com')).toBe(true);
    expect(isValidEmail('not-an-email')).toBe(false);
  });

  it('requires username and password on login', () => {
    const empty = validateLoginForm({ username: '', password: '' });
    expect(empty.isValid).toBe(false);
    expect(empty.errors.username).toBeTruthy();
    expect(empty.errors.password).toBeTruthy();

    const ok = validateLoginForm({ username: 'alice', password: 'secret' });
    expect(ok.isValid).toBe(true);
  });

  it('enforces register rules', () => {
    const bad = validateRegisterForm({
      username: 'ab',
      email: 'bad',
      password: 'short',
    });
    expect(bad.isValid).toBe(false);
    expect(bad.errors.username).toBeTruthy();
    expect(bad.errors.email).toBeTruthy();
    expect(bad.errors.password).toBeTruthy();

    const good = validateRegisterForm({
      username: 'alice',
      email: 'alice@example.com',
      password: 'SecurePass1!',
    });
    expect(good.isValid).toBe(true);

    const lettersOnly = validateRegisterForm({
      username: 'alice',
      email: 'alice@example.com',
      password: 'abcdefghijkl',
    });
    expect(lettersOnly.isValid).toBe(false);
    expect(lettersOnly.errors.password).toBeTruthy();
  });

  it('validates BYOC AWS step 1 access keys', () => {
    const missing = validateByocAwsStep1({
      method: 'access_keys',
      awsForm: { region: 'ap-south-1' },
    });
    expect(missing.isValid).toBe(false);

    const ok = validateByocAwsStep1({
      method: 'access_keys',
      awsForm: {
        access_key_id: 'AKIA',
        secret_access_key: 'secret',
        region: 'ap-south-1',
      },
    });
    expect(ok.isValid).toBe(true);
  });
});
