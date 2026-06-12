import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FaLock, FaTimes } from 'react-icons/fa';
import { PATHS } from '../../data/productFacts.js';
import '../../styles/plan-upgrade.css';

export default function PlanUpgradeDrawer({
  open,
  onClose,
  featureLabel,
  currentPlan,
  requiredPlan,
}) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="plan-upgrade-drawer-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="plan-upgrade-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="plan-upgrade-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="plan-upgrade-drawer__close" onClick={onClose} aria-label="Close">
          <FaTimes />
        </button>
        <div className="plan-upgrade-drawer__icon" aria-hidden="true">
          <FaLock />
        </div>
        <h2 id="plan-upgrade-drawer-title">Upgrade required</h2>
        <p className="plan-upgrade-drawer__feature">{featureLabel}</p>
        <p>
          You are on <strong>{currentPlan}</strong>. This requires <strong>{requiredPlan}</strong> or above.
        </p>
        <Link to={PATHS.pricing} className="plan-upgrade-gate__cta" onClick={onClose}>
          Compare plans
        </Link>
      </aside>
    </div>
  );
}
