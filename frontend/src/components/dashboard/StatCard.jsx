import React from 'react';

function StatCard({ title, value, icon }) {
  return (
    <div className="stat-card">
      <div className="card-icon">{icon}</div>
      <div className="card-content">
        <h3 className="card-title">{title}</h3>
        <p className="card-value">{value}</p>
      </div>
    </div>
  );
}

export default StatCard;
