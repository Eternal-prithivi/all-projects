import React from 'react';

function StatCard({ title, value, icon, trend, trendValue, subtitle, action, type }) {
  return (
    <div className="stat-card" data-type={type}>
      <div className="stat-card-header">
        <div className="stat-icon">{icon}</div>
        {action && <div className="card-action">{action}</div>}
      </div>
      <div className="card-content">
        <h3 className="card-title">{title}</h3>
        <p className="card-value">{value}</p>
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
        {trend && trendValue && (
          <p className={`card-trend ${trend}`}>
            {trend === 'up' ? '↑' : '↓'} {trendValue}
          </p>
        )}
      </div>
    </div>
  );
}

export default StatCard;
