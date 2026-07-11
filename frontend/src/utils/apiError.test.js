import { describe, expect, it } from 'vitest';
import { getApiErrorMessage } from '../api.js';

describe('getApiErrorMessage', () => {
  it('formats FastAPI validation error arrays as readable text', () => {
    const err = {
      response: {
        data: {
          detail: [
            {
              type: 'greater_than_equal',
              loc: ['query', 'limit'],
              msg: 'Input should be greater than or equal to 5',
              input: '2',
              ctx: { ge: 5 },
            },
          ],
        },
      },
    };
    expect(getApiErrorMessage(err, 'fallback')).toBe(
      'query.limit: Input should be greater than or equal to 5'
    );
  });

  it('returns string detail unchanged', () => {
    const err = { response: { data: { detail: 'Not found' } } };
    expect(getApiErrorMessage(err, 'fallback')).toBe('Not found');
  });

  it('handles structured Zenith detail objects', () => {
    const err = {
      response: {
        data: {
          detail: { message: 'Connect AWS first', setup_steps: ['Open Settings'] },
        },
      },
    };
    expect(getApiErrorMessage(err, 'fallback')).toBe('Connect AWS first Open Settings');
  });

  it('shows remote API host on production network errors', () => {
    const err = { message: 'Network Error' };
    const prevMode = import.meta.env.MODE;
    import.meta.env.MODE = 'production';
    try {
      const msg = getApiErrorMessage(err, 'fallback');
      expect(msg).toContain('zenith-backend-707i.onrender.com');
      expect(msg).not.toContain('localhost:8000');
    } finally {
      import.meta.env.MODE = prevMode;
    }
  });
});
