import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/quick-actions.css';

const QuickActions = () => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  // Detect platform for display
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 || 
                navigator.userAgent.toUpperCase().indexOf('MAC') >= 0;
  const modifierKey = isMac ? '⌥' : 'Alt';

  const actions = [
    {
      id: 'vm',
      label: 'Request VM',
      icon: '🖥️',
      shortcut: `${modifierKey} + Shift + N`,
      onClick: () => {
        navigate('/dashboard/vmcluster');
      }
    },
    {
      id: 'upload',
      label: 'Upload File',
      icon: '📤',
      shortcut: `${modifierKey} + Shift + U`,
      onClick: () => {
        navigate('/dashboard/storage');
      }
    },
    {
      id: 'costs',
      label: 'View Costs',
      icon: '💰',
      shortcut: `${modifierKey} + Shift + C`,
      onClick: () => {
        navigate('/dashboard/costs');
      }
    },
    {
      id: 'docs',
      label: 'Documentation',
      icon: '📚',
      shortcut: '?',
      onClick: () => {
        navigate('/help');
      }
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
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsOpen(false);
                action.onClick();
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
