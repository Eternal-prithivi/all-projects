import React, { useEffect } from "react";
import { createPortal } from "react-dom";
import "../../styles/provision.css";
import "../../styles/zenith-wizard.css";

/**
 * Shared step chrome (Terraform-style) for Security / Storage wizards.
 */
export function WizardNote({ title = "What happens next", children, variant = "info" }) {
  return (
    <div className={`zenith-wizard-note zenith-wizard-note--${variant}`} role="note">
      {title && <strong className="zenith-wizard-note__title">{title}</strong>}
      <div className="zenith-wizard-note__body">{children}</div>
    </div>
  );
}

export default function ZenithWizardFrame({
  title,
  subtitle,
  stepLabels,
  currentStep,
  onStepClick,
  onClose,
  children,
  footer,
  className = "",
}) {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return createPortal(
    <div className="zenith-wizard-overlay" role="dialog" aria-modal="true">
      <div
        className={`zenith-wizard-panel ${className}`.trim()}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="zenith-wizard-panel__header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p className="zenith-wizard-panel__subtitle">{subtitle}</p>}
          </div>
          {onClose && (
            <button type="button" className="zenith-wizard-close" onClick={onClose} aria-label="Close">
              ×
            </button>
          )}
        </header>

        <div className="wizard-steps zenith-wizard-steps">
          {stepLabels.map((label, i) => (
            <React.Fragment key={label}>
              <div
                className={`wizard-step ${
                  i === currentStep ? "active" : i < currentStep ? "completed" : "inactive"
                }`}
                onClick={() => onStepClick?.(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && i < currentStep) onStepClick?.(i);
                }}
                role={i < currentStep ? "button" : undefined}
                tabIndex={i < currentStep ? 0 : undefined}
              >
                <div className="wizard-step-number">{i < currentStep ? "✓" : i + 1}</div>
                <span className="wizard-step-label">{label}</span>
              </div>
              {i < stepLabels.length - 1 && (
                <div className={`wizard-step-connector ${i < currentStep ? "completed" : ""}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        <div className="zenith-wizard-panel__body">{children}</div>

        {footer && <footer className="zenith-wizard-panel__footer">{footer}</footer>}
      </div>
    </div>,
    document.body
  );
}
