import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import ZenithModal from '../components/ui/ZenithModal.jsx';
import Button from '../components/ui/Button.jsx';

const ConfirmContext = createContext(null);

const DEFAULT_OPTIONS = {
  title: 'Confirm action',
  message: 'Are you sure you want to continue?',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  variant: 'primary',
};

export function ConfirmProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [busy, setBusy] = useState(false);
  const resolverRef = useRef(null);

  const close = useCallback((result) => {
    setOpen(false);
    setBusy(false);
    const resolve = resolverRef.current;
    resolverRef.current = null;
    if (resolve) resolve(result);
  }, []);

  const confirm = useCallback((opts = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setOptions({ ...DEFAULT_OPTIONS, ...opts });
      setOpen(true);
    });
  }, []);

  const handleConfirm = useCallback(async () => {
    if (options.onConfirm) {
      try {
        setBusy(true);
        await options.onConfirm();
        close(true);
      } catch {
        setBusy(false);
      }
      return;
    }
    close(true);
  }, [close, options]);

  const value = useMemo(() => ({ confirm }), [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      <ZenithModal
        open={open}
        onClose={() => close(false)}
        title={options.title}
        subtitle={options.message}
        footer={
          <>
            <Button variant="secondary" type="button" onClick={() => close(false)} disabled={busy}>
              {options.cancelLabel}
            </Button>
            <Button
              variant={options.variant === 'danger' ? 'danger' : 'primary'}
              type="button"
              onClick={handleConfirm}
              disabled={busy}
            >
              {busy ? 'Working…' : options.confirmLabel}
            </Button>
          </>
        }
      />
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) {
    throw new Error('useConfirm must be used within ConfirmProvider');
  }
  return ctx;
}

/**
 * Drop-in helper for pages not yet wrapped — falls back to window.confirm.
 */
export async function confirmAction(options, fallbackConfirm = window.confirm) {
  const message = [options.title, options.message].filter(Boolean).join('\n\n');
  return fallbackConfirm(message);
}
