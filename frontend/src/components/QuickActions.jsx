import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/quick-actions.css';

const QuickActions = () => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  const actions = [
    {
      id: 'vm',
      label: 'Request VM',
      icon: '🖥️',
      shortcut: 'N',
      onClick: () => navigate('/vm-cluster')
    },
    {
      id: 'upload',
      label: 'Upload File',
      icon: '📤',
      shortcut: 'U',
      onClick: () => navigate('/storage')
    },
    {
      id: 'costs',
      label: 'View Costs',
      icon: '💰',
      shortcut: 'C',
      onClick: () => navigate('/dashboard')
    },
    {
      id: 'docs',
      label: 'Documentation',
      icon: '📚',
      shortcut: '?',
      onClick: () => window.open('#', '_blank')
    }
  ];

  return (
    <div className="quick-actions">
      <button 
        className={`quick-actions-trigger ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Quick actions"
      >
        {isOpen ? '✕' : '⚡'}
      </button>

      {isOpen && (
        <div className="quick-actions-menu">
          <div className="quick-actions-header">
            Quick Actions
          </div>
          {actions.map((action) => (
            <button
              key={action.id}
              className="quick-action-item"
              onClick={() => {
                action.onClick();
                setIsOpen(false);
              }}
            >
              <span className="quick-action-icon">{action.icon}</span>
              <span className="quick-action-label">{action.label}</span>
              <kbd className="quick-action-shortcut">{action.shortcut}</kbd>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default QuickActions;
