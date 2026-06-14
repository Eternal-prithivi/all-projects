import React from 'react';

export function KpiTile({ label, value, hint, className = '' }) {
  return (
    <div className={['enterprise-kpi', className].filter(Boolean).join(' ')}>
      {label ? <span className="enterprise-kpi__label">{label}</span> : null}
      <div className="enterprise-kpi__value">{value}</div>
      {hint ? <div className="enterprise-kpi__hint">{hint}</div> : null}
    </div>
  );
}

export default function KpiStrip({ children, className = '' }) {
  return (
    <div className={['enterprise-kpi-strip', className].filter(Boolean).join(' ')}>
      {children}
    </div>
  );
}
