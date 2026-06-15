import React from 'react';

/**
 * Bento-grid compatible stat card.
 * 
 * @param {string} title - Card title (uppercase label)
 * @param {string|number} value - Main display value
 * @param {React.ReactNode} icon - Icon element
 * @param {string} trend - 'up' or 'down'
 * @param {string} trendValue - e.g. "+12.5%"
 * @param {string} subtitle - Secondary text below value
 * @param {React.ReactNode} action - Action button element
 * @param {string} type - Card type for color coding ('costs', 'vms', 'storage', 'security')
 * @param {string} size - Bento grid size ('lg', 'md', 'sm')
 * @param {React.ReactNode} children - Content below the header (charts, rings, etc.)
 */
function StatCard({ title, value, icon, trend, trendValue, subtitle, action, type, size = 'md', children, ...rest }) {
  return (
    <div className={`bento-card size-${size}`} data-type={type} {...rest}>
      <div className="stat-card-header">
        <div className="stat-icon">{icon}</div>
        <h3 className="card-title">{title}</h3>
        {action && <div className="card-action">{action}</div>}
      </div>
      <div className="card-content">
        {value !== undefined && <p className="card-value">{value}</p>}
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
        {trend && trendValue && (
          <p className={`card-trend ${trend}`}>
            {trend === 'up' ? '↑' : '↓'} {trendValue}
          </p>
        )}
      </div>
      {/* Chart/Ring/Custom content area */}
      {children && (
        <div className="card-chart-area">
          {children}
        </div>
      )}
    </div>
  );
}

export default StatCard;
