import React, { useEffect, useMemo } from 'react';
import { commandKeyLabel } from '../utils/keyboardShortcuts';
import '../styles/keyboard-shortcuts.css';

const KeyboardShortcuts = ({ isOpen, onClose, variant = 'dashboard' }) => {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const sections = useMemo(() => {
    const mod = commandKeyLabel();
    const general = {
      title: 'General',
      items: [
        { key: `${mod} + K`, description: 'Open command palette' },
        { key: '?', description: 'Show keyboard shortcuts' },
        { key: 'Esc', description: 'Close dialogs and palettes' },
      ],
    };

    if (variant === 'admin') {
      return [
        general,
        {
          title: 'Go to (press G, then key)',
          items: [
            { key: 'G → D', description: 'Admin overview' },
            { key: 'G → U', description: 'User management' },
            { key: 'G → A', description: 'Analytics' },
            { key: 'G → S', description: 'System health' },
          ],
        },
      ];
    }

    return [
      general,
      {
        title: 'Go to (press G, then key)',
        items: [
          { key: 'G → D', description: 'Dashboard home' },
          { key: 'G → V', description: 'VM cluster' },
          { key: 'G → S', description: 'Storage' },
          { key: 'G → C', description: 'Cost analysis' },
          { key: 'G → Y', description: 'Security vault' },
        ],
      },
    ];
  }, [variant]);

  if (!isOpen) return null;

  return (
    <div className="keyboard-shortcuts-overlay" onClick={onClose} role="presentation">
      <div
        className="keyboard-shortcuts-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
      >
        <div className="shortcuts-header">
          <h2>Keyboard shortcuts</h2>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="shortcuts-list">
          {sections.map((section) => (
            <div key={section.title} className="shortcuts-section">
              <h3 className="shortcuts-section-title">{section.title}</h3>
              {section.items.map((shortcut) => (
                <div key={shortcut.key} className="shortcut-item">
                  <kbd className="shortcut-key">{shortcut.key}</kbd>
                  <span className="shortcut-description">{shortcut.description}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="shortcuts-footer">
          <p>
            Shortcuts are disabled while typing in a field. Press <kbd>Esc</kbd> to close.
          </p>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcuts;
