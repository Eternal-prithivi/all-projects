import React from 'react';
import '../styles/emptystate.css';

const EmptyState = ({ 
  icon = '📭', 
  title = 'No data yet', 
  message = 'Get started by creating something new',
  actionLabel = null,
  onAction = null 
}) => {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-message">{message}</p>
      {actionLabel && onAction && (
        <button className="empty-state-action" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
};

export default EmptyState;
