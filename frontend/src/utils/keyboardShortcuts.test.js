import { describe, expect, it } from 'vitest';
import { isTypingTarget } from './keyboardShortcuts';

describe('isTypingTarget', () => {
  it('returns true for input, textarea, and select', () => {
    expect(isTypingTarget({ tagName: 'INPUT', isContentEditable: false })).toBe(true);
    expect(isTypingTarget({ tagName: 'TEXTAREA', isContentEditable: false })).toBe(true);
    expect(isTypingTarget({ tagName: 'SELECT', isContentEditable: false })).toBe(true);
  });

  it('returns true for contenteditable elements', () => {
    expect(isTypingTarget({ tagName: 'DIV', isContentEditable: true })).toBe(true);
  });

  it('returns false for non-editable elements', () => {
    expect(isTypingTarget({ tagName: 'BUTTON', isContentEditable: false })).toBe(false);
    expect(isTypingTarget({ tagName: 'DIV', isContentEditable: false, closest: () => null })).toBe(
      false,
    );
  });
});
