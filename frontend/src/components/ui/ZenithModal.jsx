import { useEffect } from "react";
import { createPortal } from "react-dom";
import "../../styles/zenith-modal.css";

/**
 * Portaled dialog — avoids backdrop-filter parents clipping fixed overlays.
 */
export default function ZenithModal({
  open,
  onClose,
  title,
  subtitle,
  titleId = "zenith-modal-title",
  children,
  footer,
  wide = false,
  large = false,
}) {
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const panelClass = [
    "zenith-modal-panel",
    wide && "zenith-modal-panel--wide",
    large && "zenith-modal-panel--large",
  ]
    .filter(Boolean)
    .join(" ");

  return createPortal(
    <div className="zenith-modal-overlay" onClick={onClose} role="presentation">
      <div
        className={panelClass}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="zenith-modal-header">
          <div className="zenith-modal-header__text">
            <h3 id={titleId}>{title}</h3>
            {subtitle && <p className="zenith-modal-subtitle">{subtitle}</p>}
          </div>
          <button
            type="button"
            className="zenith-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </header>
        <div className="zenith-modal-body">{children}</div>
        {footer ? <footer className="zenith-modal-footer">{footer}</footer> : null}
      </div>
    </div>,
    document.body
  );
}
