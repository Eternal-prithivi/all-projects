import { createPortal } from 'react-dom';
import '../styles/twofa-modal.css';

const ShieldIcon = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const LockOffIcon = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 9.9-1" />
  </svg>
);

/**
 * Zenith-styled 2FA modal (portaled). Used on Security vault + Security settings.
 */
export default function TwoFADialog({
  open,
  onClose,
  titleId,
  title,
  description,
  kicker = 'Account security',
  variant = 'default',
  children,
  primaryLabel,
  onPrimary,
  primaryVariant = 'primary',
  cancelLabel = 'Cancel',
  onCancel,
}) {
  if (!open) return null;

  const iconClass =
    variant === 'danger'
      ? 'twofa-panel__icon twofa-panel__icon--danger'
      : 'twofa-panel__icon';

  const handleCancel = onCancel || onClose;

  return createPortal(
    <div
      className="twofa-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={onClose}
    >
      <div className="twofa-panel" onClick={(e) => e.stopPropagation()}>
        <div className="twofa-panel__gold-bar" aria-hidden />
        <button
          type="button"
          className="twofa-panel__close"
          onClick={onClose}
          aria-label="Close dialog"
        >
          ×
        </button>
        <div className="twofa-panel__scroll">
          <header className="twofa-panel__header">
            <div className={iconClass}>
              {variant === 'danger' ? <LockOffIcon /> : <ShieldIcon />}
            </div>
            <span className="twofa-panel__kicker">{kicker}</span>
            <h3 id={titleId} className="twofa-title">
              {title}
            </h3>
          </header>
          <div className="twofa-panel__body">
            {description ? <p className="twofa-description">{description}</p> : null}
            {children}
            {(primaryLabel || cancelLabel) && (
              <div className="twofa-panel__actions">
                {primaryLabel ? (
                  <button
                    type="button"
                    className={`twofa-btn twofa-btn--${primaryVariant}`}
                    onClick={onPrimary}
                  >
                    {primaryLabel}
                  </button>
                ) : null}
                {cancelLabel ? (
                  <button type="button" className="twofa-panel__cancel-link" onClick={handleCancel}>
                    {cancelLabel}
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
