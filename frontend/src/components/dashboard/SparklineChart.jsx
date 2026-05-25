import React from 'react';
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from 'recharts';

/**
 * Gold-gradient sparkline area chart for the dashboard.
 * Wraps Recharts AreaChart with Zenith theming.
 * 
 * @param {Array} data - Array of { name, value } objects
 * @param {number} height - Chart height in pixels (default: 120)
 * @param {boolean} showTooltip - Whether to show tooltip on hover
 * @param {boolean} showXAxis - Whether to show X axis labels
 */
function SparklineChart({ data = [], height = 120, showTooltip = true, showXAxis = false }) {
  if (!data || data.length === 0) return null;

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="sparkline-tooltip">
          <p className="sparkline-tooltip-label">{label}</p>
          <p className="sparkline-tooltip-value">${payload[0].value.toLocaleString()}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="sparkline-chart-wrapper">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
          <defs>
            <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffd700" stopOpacity={0.4} />
              <stop offset="50%" stopColor="#d4af37" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#d4af37" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="goldStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#ffd700" />
              <stop offset="100%" stopColor="#d4af37" />
            </linearGradient>
          </defs>
          {showXAxis && (
            <XAxis 
              dataKey="name" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'Inter' }}
              dy={8}
            />
          )}
          {showTooltip && <Tooltip content={<CustomTooltip />} />}
          <Area
            type="monotone"
            dataKey="value"
            stroke="url(#goldStroke)"
            strokeWidth={2.5}
            fill="url(#goldGradient)"
            dot={false}
            activeDot={{ 
              r: 5, 
              fill: '#ffd700', 
              stroke: '#000', 
              strokeWidth: 2 
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default SparklineChart;
